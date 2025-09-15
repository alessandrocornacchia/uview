from dotenv import load_dotenv
import os
import sys
import subprocess
import argparse
from pathlib import Path


parser = argparse.ArgumentParser(description='Run an experiment')
parser.add_argument('-e', '--exp-id', type=str, help='Experiment ID', required=True)
parser.add_argument('-c', '--config', type=str, 
                    help='Configuration profiles. Available profiles ' + ','.join(os.listdir(f'./configs')), 
                    default='quick-test')
parser.add_argument("--loadgen", action='store_true', help="Start the load generator")
parser.add_argument("--chaos", action='store_true', help="Start the anomaly injector")


args = parser.parse_args()

dotenv_path = args.exp_id + '/.env'

# looks for .env file in the current directory and loads it
if not os.path.exists(dotenv_path):
    print(f"❌ Error: .env file not found at {dotenv_path}. Make sure your experiment directory {args.exp_id} exists and contains .env file.")
    sys.exit(1)
else:
    load_dotenv(dotenv_path)


# ---- here we load environment variables ------
print(f"🏁 Loading environment {dotenv_path}. Using configuration profile: {args.config}")

# this is the directory where experiment artifacts are stored. 
# If nor provided, will use the current directory
try:
    dataset_dir = os.path.expandvars(os.environ.get('DATASET_DIR'))
except: 
    dataset_dir = './'

root_dir = os.path.expandvars(os.environ.get('PROJECT_ROOT'))
loadgen_host = os.path.expandvars(os.environ.get('LOADGEN_HOST'))
loadgen_dir = os.path.expandvars(os.environ.get('LOADGEN_DIR'))
anomaly_injector_cmd = os.path.expandvars(os.environ.get('ANOMALY_INJECTOR_CMD'))
app = os.path.expandvars(os.environ.get('APP'))
build_name = os.path.expandvars(os.environ.get('BUILD_NAME'))
app_dir = os.path.expandvars(os.environ.get('APP_DIR'))


# ---- here we load environment variables ------

def main(config):
    
    experiment_id = config.exp_id
    profile = config.config


    # Create directories for datasets
    experiment_path = Path(f"{dataset_dir}/{experiment_id}").absolute()
    experiment_path.mkdir(parents=True, exist_ok=True)
    (experiment_path / 'metrics').mkdir(parents=True, exist_ok=True)
    (experiment_path / 'traces').mkdir(parents=True, exist_ok=True)

    # Get configuration profile chosen by the user
    profile_path = Path(f"{dataset_dir}/configs/{profile}")
    if not profile_path.exists():
        print(f"Profile {profile} not found in {profile_path}")
        sys.exit(1)

    # copy confiuration files for load generation and chaos engineering to the experiment directory for later reference
    if config.loadgen:
        os.system(f"cp {profile_path}/{app}.json {experiment_path}")
    if config.chaos:
        os.system(f"cp {profile_path}/injector.yaml {experiment_path}")

    # Run the microservice app
    cmd = f"{app_dir}/deploy-microservices.sh {app} {build_name}"
    ret = os.system(cmd)
    if ret != 0:
        print(f"Error starting microservice app {app}")
        sys.exit(1)

    if config.loadgen:
        # Run the load generator on the desired node
        print(f"Starting workload generator on {loadgen_host}")

        loadgen_cmd = f'./wrk_http -config={profile_path.absolute()}/{app}.json ' \
                    f'-outfile="{experiment_path}/traces/latency.csv" &> {experiment_path}/loadgen.log &'


        print("")
        print("=== LOAD GENERATOR ===")
        print(f"Starting async load generator for user requests. Running on: {loadgen_host}.") 
        print(f"{loadgen_cmd}")
        
        cmd = f'ssh {loadgen_host} "cd {experiment_path} ; set -a ; source .env ; cd {loadgen_dir}; {loadgen_cmd}"'
        ret = os.system(cmd)
        if ret != 0:
            print(f"Error starting workload generator on {loadgen_host}")
            sys.exit(1)


    if config.chaos:
        # Run the anomaly injector locally
        cmd = f"{anomaly_injector_cmd} -c {experiment_path}/injector.yaml -o {experiment_path}/faults.csv"
        
        print("")
        print("=== ANOMALY INJECTION ===")
        print(f"Running anomaly injector with command: {cmd}")

        with open(f"{dataset_dir}/{experiment_id}/anomalies.log", "w") as outfile:
            ret = subprocess.call(cmd, stdout=outfile, stderr=outfile, shell=True)
            if ret != 0:
                print(f"\n\n ! Error running anomaly injector. Log file tail:\n")
                os.system(f"tail -n10 {dataset_dir}/{experiment_id}/anomalies.log")

                if config.loadgen:
                    print(f"\nKilling the load generator on {loadgen_host}...")
                    if os.system(f"ssh {loadgen_host} 'pkill wrk_http'") != 0:
                        print(f"Error killing the load generator on {loadgen_host}")

                sys.exit(1)

    print("")
    print("=== TEAR DOWN WORKLOAD ===")
    cmd = f"{app_dir}/deploy-microservices.sh {app} {build_name} --down"
    ret = os.system(cmd)
    if ret != 0:
        print(f"Error destorying microservice app {app}")
        sys.exit(1)


# execute
main(args)