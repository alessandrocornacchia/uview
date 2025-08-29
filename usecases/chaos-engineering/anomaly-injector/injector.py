import os
import random

import subprocess
import time
import argparse
import yaml
import logging
import datetime
from pytimeparse.timeparse import timeparse
from chaos_mesh_client import ChaosMeshStressInjector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# available stressors
commands = {
    # "firm-cpu": './cpu %d',
    "mem_bw": './mem %d',    # memory bandwidth contention
    "llc": './l3 %d',        # cache contention (check linux perf metrics from node_exporter such as offcore_response.*.llc_hit/miss.local_DRAM)
    "io": 'sysbench fileio --file-total-size=%s --file-test-mode=rndrw --time=%d --threads=%d run',
    # "net-loss": 'sudo tc qdisc %s dev %s root tbf rate %dkbit burst %d latency 0ms',
    # "net-delay": 'sudo tc qdisc %s dev %s root netem delay %dms %dms',
    "cpu": 'stress-ng --cpu %d --timeout %ds --metrics-brief',
    "mem_capacity": 'stress-ng --vm %d --vm-bytes %s --timeout %ds'    # workers, bytes, duration
}


dev = 'eth0'

location = '/anomaly'

## these can be service dependent (use external config file..)
disk = 150   # file size: Gb
threads = 1
rate = 1024  # bandwidth limit: kbit

limit = 1024 #
latency = 50 # network delay: ms
burst = 1024 # bucket size
duration = 10  # sec

ncpu = 1 # number of cpus to stress
membytes = '1G' # written memory size
intensity = random.randint(0, 100)


parser = argparse.ArgumentParser(description='Inject anomalies in the system. Available anomalies: ' + ', '.join(commands.keys()))
parser.add_argument('-c', '--config', type=str, help='Path to the configuration file', required=True)
parser.add_argument('-d', '--dry-run', action='store_true', help='Dry run (do not execute commands)')
parser.add_argument('-o', '--output', type=str, help='Output csv file with anomaly injection details', default='./latency.csv')


def get_containers_docker_compose(config, services_only=True):
    # get the list of containers from the docker-compose file
    
    try:
        app = os.environ['APP']
    except KeyError:
        app = config['app']

    try:
        app_dir = os.environ['APP_DIR']
    except KeyError:
        app_dir = config['app_dir']

    try:
        build_name = os.environ['BUILD_NAME']
    except KeyError:
        build_name = config['build_name']

    compose_dir = os.path.join(app_dir, app, 'build', build_name, 'docker')
    command = f'cd {compose_dir} && docker --log-level error compose ps --services'
        
    out = subprocess.check_output(command, shell=True)
    out = out.decode('utf-8')
    containers = out.strip('\n').split('\n')

    if services_only:
        containers = [c for c in containers if 'service' in c]

    return containers


def get_containers_k8s(config):
    # get the list of microservice labels using kubectl
    try:
        namespace = config.get('namespace', 'default')
        
        # Get all pods in the specified namespace
        # command = f'kubectl get pods -n {namespace} --no-headers -o custom-columns=":metadata.name"'
        command = f"kubectl get pods -n {namespace} -o custom-columns=':metadata.labels.app' --no-headers"

        out = subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL)
        out = out.decode('utf-8')
        pods = out.strip().split('\n')
        
        # Filter out empty strings
        pods = [pod.strip() for pod in pods if pod.strip()]
        
        # Filter out pods that contain any of the blacklist keywords
        blacklist = config.get('blacklist', [])
        if blacklist:
            filtered_pods = []
            for pod in pods:
                if not any(black in pod for black in blacklist):
                    filtered_pods.append(pod)
            pods = filtered_pods
        
        return pods
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get pods from kubectl: {e}")
        return []
    except Exception as e:
        logging.error(f"Error getting containers from Kubernetes: {e}")
        return []

def inject(containers, config, dry_run=False, output=None, client=None):

    # get the at random targets (ranging from 1 to all containers)
    num_targets = random.randint(1, len(containers))
    logging.info('====== # of targets: ' + str(num_targets) + ' =======')
    targets = set()
    i = 0
    while i < num_targets:
        target = random.randint(0, len(containers) - 1)
        if target not in targets:
            targets.add(target)
            i += 1
    logging.info("Selected targets are: " + ",".join([ containers[t] for t in targets]))

    configured_commands = config.keys()

    for i in targets:
        # number of anomaly types to inject from those available in the configuration
        num_types = random.randint(1, len(config.keys()))
        logging.info(f'[{containers[i]}] # of anomaly types to inject: ' + str(num_types))
        types = set()
        
        # select num_types at random from the pool of available anomalies
        j = 0
        while j < num_types:
            # select a random anomaly
            k = random.randint(0, len(config.keys()) - 1)
            anomaly_key = list(config.keys())[k]
            
            # add it if not already selected
            if anomaly_key not in types:
                types.add(anomaly_key)
                j += 1
        logging.info(f"Selected anomalies for {containers[i]}: " + ','.join(types))
        
        durations = []
        timestamp_start = None

        for anomaly_key in types:

            # compute duration (considering random_min_duration if specified)
            duration = int(config[anomaly_key]["duration"])
            if config[anomaly_key]["random_min_duration"]:
                duration = random.randint(config[anomaly_key]["random_min_duration"], duration)
            durations.append(duration)

            if client is not None:
                
                # Kubernetes + Chaos Mesh
                
                logging.info(f"Injecting {anomaly_key} in {containers[i]} using Chaos Mesh...")
                
                microservice = containers[i]
                duration_str = str(duration) + "s"
                
                if anomaly_key == "cpu":
                    workers = config[anomaly_key]["ncpu"]
                    load = config[anomaly_key].get("load", 100)
                    if not dry_run:
                        client.inject_cpu_stress(microservice, duration_str, workers, load=load)
                elif anomaly_key == "mem_capacity":
                    workers = config[anomaly_key]["threads"]
                    size = config[anomaly_key]["size"]
                    if not dry_run:
                        client.inject_memory_stress(microservice, duration_str, workers, size)
                
            else:
                
                # Docker Compose + FIRM
                
                # command = 'ssh '+username+pswd+'@' + nodes[i] + ' "cd ' + location + '; '
                command = 'docker exec ' + 'docker-' + containers[i] + '-1' + ' /bin/sh -c "cd ' + location + ' ; '

                if anomaly_key == "mem-bw":
                    # memory - ./mem %d
                    command += commands[anomaly_key] % duration + '"' # (duration, intensity)
                elif anomaly_key == "llc":
                    # llc - ./l3 %d
                    command += commands[anomaly_key] % config['llc']["duration"] + '"' # (duration, intensity)
                elif anomaly_key == "io":
                    # io - sysbench fileio --file-total-size=%dG --file-test-mode=rndrw --time=%d --threads=%d run
                    # this can be quite intrusive for the system (pay attention to the size of the files you generate)
                    prepare_command = 'sysbench fileio --file-total-size=%s prepare' % config['io']["size"]
                    run_command = commands[anomaly_key] % (config['io']["size"], duration, config['io']["threads"])
                    clean_command = 'sysbench fileio --file-total-size=%s cleanup' % config['io']["size"]               
                    command += prepare_command + '; ' + run_command + '; ' + clean_command + '"'
                    #command += 'cd test-files; ' + commands[anomaly_type] % (disk, duration, threads) + '"' # (duration, threads, intensity)
                elif anomaly_key == "net-loss":    #  not used
                    # network - tc
                    command += commands[anomaly_key] % ('add', dev, rate, burst) + '; sleep ' + str(duration) + '; ' + commands[anomaly_key] % ('delete', dev, rate, burst) + '"'
                elif anomaly_key == "net-delay": #  not used
                    # network delay - tc
                    command += commands[anomaly_key] % ('add', dev, latency, latency/10) + '; sleep ' + str(duration) + '; ' + commands[anomaly_key] % ('delete', dev, latency, latency/10) + '"'
                elif anomaly_key == "cpu":
                    command += commands[anomaly_key] % (config['cpu']['ncpu'], duration) + '"'
                elif anomaly_key == "mem_capacity":
                    command += commands[anomaly_key] % (config['mem_capacity']['threads'], config['mem_capacity']['size'], duration) + '"'

                logging.info("Executing: " + command)
            
                if not dry_run:
                    subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
                # os.system(command)
                # scmd = shlex.split(command)
                # print(scmd)
            
            timestamp_start = datetime.datetime.now()
            
            # Write to file
            # caveat: we don't actually now when anomaly will start and end from here 
            # we assume it starts immediately (not so critical unless anomaly lasts a sub-seconds...)
            
            if output:
                with open(output, 'a') as f:
                    timestamp_end = timestamp_start + datetime.timedelta(seconds=duration)
                    f.write(timestamp_start.astimezone().strftime("%Y-%m-%d %H:%M:%S%z") + ',')
                    f.write(f"{timestamp_end.astimezone().strftime('%Y-%m-%d %H:%M:%S%z')},")
                    f.write(f"{containers[i]}\n")
            
            # injection loop over anoamlies continue..
        # injection loop over containers continue.. 
    return durations
                



if __name__=="__main__":

    hostname = os.uname()[1]
    logging.info(f'Running on host {hostname}.')

    args = parser.parse_args()
    
    # read yaml configuration file
    with open(args.config, 'r') as f:
        logging.info(f'Reading configuration file {args.config}...')
        config = yaml.load(f, Loader=yaml.FullLoader)
    
    anomaly_injector_client = None
    
    if 'namespace' in config:
        logging.info(f'Detected Kubernetes deployment. Using namespace {config["namespace"]} and using Chaos Mesh for anomaly injection...')
        containers = get_containers_k8s(config)
        anomaly_injector_client = ChaosMeshStressInjector(config.get('namespace', None))

    else:
        containers = get_containers_docker_compose(config)
    
    logging.info(f'Found containers {containers}')

    if len(containers) == 0:
        logging.error('No containers found. Please check your configuration and ensure that the Docker Compose file is correct.')
        exit(1)
        
    with open(args.output, 'w') as f:
        logging.info(f'Injected anomalies details written to {args.output}...')
        f.write('start,end,service\n')

    try:
        start_delay_seconds = timeparse(config['anomalies']['start_delay'])
    except Exception as e:
        logging.error(f"Start delay not specified. Using default value of 0 seconds.")
        start_delay_seconds = 0

    logging.info(f"Waiting for {start_delay_seconds} before starting injection...")
    time.sleep(start_delay_seconds)

    
    try:
        # inject anomalies in a given number of rounds
        for i in range(config['anomalies']['num_injection_rounds']):
            
            try:
                durations = inject(
                    containers,
                    config['anomalies']['stressors'], 
                    dry_run=args.dry_run,
                    output=args.output,
                    client=anomaly_injector_client
                )
            except Exception as e:
                logging.error(f"❌ Error during anomaly injection: {e}")
                raise e
            
            # Here anomaly has been injected in selected targets, we wait until next anomaly injection round
            logging.info(f'Injection round {i} completed...')
            
            if i < config['anomalies']['num_injection_rounds'] - 1:
                time_to_next = random.randint(1, config['anomalies']['period_max_seconds'])
                logging.info(f'Waiting for {time_to_next} seconds before next injection round...')
                
                time.sleep(time_to_next)

            else:
                # should sleep for the duration of the last anomaly, otherwise 
                # the script will exit immediately and the following log line would be misaligned in time 
                time.sleep(max(durations))
    except KeyboardInterrupt:
        logging.info("Anomaly injection interrupted by user.")
        pass

    if anomaly_injector_client:
        anomaly_injector_client.cleanup_all_experiments()

    logging.info(f"End of anomaly injection rounds.")


