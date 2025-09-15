import os
import re
import subprocess
import matplotlib.pyplot as plt
import pandas as pd
import argparse

# Configuration
REMOTE_HOST = os.getenv("REMOTE_HOST", "mcbf28")
REMOTE_PATH = os.getenv("REMOTE_PATH", "~/cornaca/microview-cp/results/")
LOCAL_PATH = os.getenv("LOCAL_PATH", "./results/IPU")

VALID_ALGOS = ["FD", "VAE", "TH"]

def download_results(force=False):
    """
    Download results from remote machine
    """
    
    # Create local directory if it doesn't exist
    os.makedirs(LOCAL_PATH, exist_ok=True)
    
    # NOTE wildcard pattern needs some care
    cmd = f"ssh {REMOTE_HOST} 'ls -d {REMOTE_PATH}/metric_*_* {REMOTE_PATH}/pods_*_* 2>/dev/null'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if len(result.stdout)==0:
        print(f"⚠️ No results found on remote machine for command {cmd}")
        print(result.stdout)
        return False
    
    remote_dirs = result.stdout.strip().split('\n')
    
    # Download each directory
    for remote_dir in remote_dirs:
        if not remote_dir:  # Skip empty lines
            continue
            
        dir_name = os.path.basename(remote_dir)
        local_dir = os.path.join(LOCAL_PATH, dir_name)
        
        # Skip if directory exists and force flag is not set
        if os.path.exists(local_dir) and not force:
            print(f"Skipping {dir_name}, already exists (use --force to override)")
            continue
        
        os.makedirs(local_dir, exist_ok=True)
        
        # Use scp to copy the files
        cmd = f"scp -r {REMOTE_HOST}:{remote_dir}/* {local_dir}/"
        print(f"Downloading: {dir_name}")
        try:
            subprocess.run(cmd, shell=True, check=True)
            print(f"✓ Successfully downloaded {dir_name} to {local_dir}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Error downloading {dir_name}: {e}")
    
    return True


def parse_wrk_output(file_path):
    """Parse wrk output file and extract requests/sec and latency"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Extract requests per second
            req_sec_match = re.search(r'Requests/sec:\s+(\d+\.\d+)', content)
            req_sec = float(req_sec_match.group(1)) if req_sec_match else None
            
            # Extract average latency
            latency_match = re.search(r'Latency\s+(\d+\.\d+)ms', content)
            latency = float(latency_match.group(1)) if latency_match else None
            
            return req_sec, latency
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None, None


def sanity_check(**kwargs):
    # can add others ...
    dir_name = kwargs.get("dir")
    algorithm = kwargs.get("algorithm")

    if algorithm not in VALID_ALGOS:
        print(f"Skipping invalid algorithm: {algorithm} for directory {dir_name}")
        return False
    return True

def to_dataframe():
    """
    Collect results from all wrk_output.txt files and create dataframes
    """
    
    metrics_results = []
    pods_results = []
    
    # 1) Process experiments of type "prometheus" for varying number of metrics
    print("Aggregating experiments:", os.listdir(LOCAL_PATH))
    for dir_name in os.listdir(LOCAL_PATH):
        if dir_name.startswith("metric_") and "prometheus" in dir_name:
            try:
                num_metrics = int(dir_name.split("_")[1])
                # TODO assumes algorithm is always at the end of the dir name
                algorithm = dir_name.split("_")[-1]
                wrk_file = os.path.join(LOCAL_PATH, dir_name, "wrk_output.txt")
                
                if os.path.exists(wrk_file):
                    req_sec, latency = parse_wrk_output(wrk_file)
                    if req_sec and latency:
                        metrics_results.append((num_metrics, req_sec, latency, algorithm))
            except (ValueError, IndexError):
                print(f"Skipping invalid directory name: {dir_name}")
    
    # 2) Process experiments of type "prometheus" for varying number of pods
    print("Aggregating experiments:", os.listdir(LOCAL_PATH))
    for dir_name in os.listdir(LOCAL_PATH):
        if dir_name.startswith("pods_") and "prometheus" in dir_name:
            try:
                num_pods = int(dir_name.split("_")[1])
                
                # NOTE assumes algorithm is always at the end of the dir name
                algorithm = dir_name.split("_")[-1]
                wrk_file = os.path.join(LOCAL_PATH, dir_name, "wrk_output.txt")
                
                if os.path.exists(wrk_file):
                    req_sec, latency = parse_wrk_output(wrk_file)
                    if req_sec and latency:
                        pods_results.append((num_pods, req_sec, latency, algorithm))
            except (ValueError, IndexError):
                print(f"Skipping invalid directory name: {dir_name}")
    
    # Convert to dataframes
    metrics_df = pd.DataFrame(metrics_results, columns=['num_metrics', 'requests_per_sec', 'latency_ms', 'algorithm'])
    pods_df = pd.DataFrame(pods_results, columns=['num_pods', 'requests_per_sec', 'latency_ms', 'algorithm'])

    metrics_df.to_csv(os.path.join(LOCAL_PATH, "prometheus_scrape_vs_metrics.csv"), index=False)
    pods_df.to_csv(os.path.join(LOCAL_PATH, "prometheus_scrape_vs_pods.csv"), index=False)
    
    # Now collect the results for the non-prometheus mode i.e., read_loop
    read_loop_metrics_results = []
    read_loop_pods_results = []
    
    # 3) Process experiments of type "read_loop" for varying number of metrics
    print("Aggregating experiments:")
    for dir_name in os.listdir(LOCAL_PATH):
        if dir_name.startswith("metric_") and "read_loop" in dir_name:
            try:
                num_metrics = int(dir_name.split("_")[1])
                algorithm = dir_name.split("_")[-1]
                if not sanity_check(dir=dir_name, algorithm=algorithm):
                    continue
                
                # Find all stats_LMAP_*.csv files in the directory
                lmap_files = [f for f in os.listdir(os.path.join(LOCAL_PATH, dir_name)) 
                             if f.startswith("stats_LMAP_") and f.endswith(".csv")]
                
                for lmap_file in lmap_files:
                    # Extract LMAP number from filename
                    lmap_number = lmap_file.split("_")[2].split(".")[0]
                    file_path = os.path.join(LOCAL_PATH, dir_name, lmap_file)
                    
                    # Read the CSV file into a dictionary
                    stats = {}
                    try:
                        with open(file_path, 'r') as f:
                            for line in f:
                                if "," in line:
                                    key, value = line.strip().split(",", 1)
                                    stats[key] = float(value)
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")
                        continue
                    
                    # Add metadata to the stats
                    stats["num_metrics"] = num_metrics
                    stats["lmap"] = lmap_number
                    stats["algorithm"] = algorithm
                    stats["num_pod"] = 8  # TODO hardcoded for now
                    stats["delta_t_seconds"] = 10  # TODO hardcoded for now

                    # Append to results
                    read_loop_metrics_results.append(stats)
            except (ValueError, IndexError) as e:
                print(f"Error processing directory {dir_name}: {e}")

    # 4) Process experiments of type "read_loop" for varying number of pods
    print("Aggregating experiments:")
    for dir_name in os.listdir(LOCAL_PATH):
        if dir_name.startswith("pods_") and "read_loop" in dir_name:
            try:
                num_pods = int(dir_name.split("_")[1])
                algorithm = dir_name.split("_")[-1]
                if not sanity_check(dir=dir_name, algorithm=algorithm):
                    continue
                
                # Find all stats_LMAP_*.csv files in the directory
                lmap_files = [f for f in os.listdir(os.path.join(LOCAL_PATH, dir_name)) 
                             if f.startswith("stats_LMAP_") and f.endswith(".csv")]
                
                for lmap_file in lmap_files:
                    # Extract LMAP number from filename
                    lmap_number = lmap_file.split("_")[2].split(".")[0]
                    file_path = os.path.join(LOCAL_PATH, dir_name, lmap_file)
                    
                    # Read the CSV file into a dictionary
                    stats = {}
                    try:
                        with open(file_path, 'r') as f:
                            for line in f:
                                if "," in line:
                                    key, value = line.strip().split(",", 1)
                                    stats[key] = float(value)
                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")
                        continue
                    
                    # Add metadata to the stats
                    stats["num_pods"] = num_pods
                    stats["lmap"] = lmap_number
                    stats["algorithm"] = algorithm
                    stats["num_metrics"] = 64  # TODO hardcoded for now
                    stats["delta_t_seconds"] = 10  # TODO hardcoded for now

                    # Append to results
                    read_loop_pods_results.append(stats)
            except (ValueError, IndexError) as e:
                print(f"Error processing directory {dir_name}: {e}")
    
    # Convert to dataframes
    if read_loop_metrics_results:
        read_loop_metrics_df = pd.DataFrame(read_loop_metrics_results)
        read_loop_metrics_df.to_csv(os.path.join(LOCAL_PATH, "read_loop_vs_metrics.csv"), index=False)
        print(f"💾 Saved read_loop_vs_metrics.csv with {len(read_loop_metrics_df)} rows and {len(read_loop_metrics_df.columns)} columns")
    
    if read_loop_pods_results:
        read_loop_pods_df = pd.DataFrame(read_loop_pods_results)
        read_loop_pods_df.to_csv(os.path.join(LOCAL_PATH, "read_loop_vs_pods.csv"), index=False)
        print(f"💾 Saved read_loop_vs_pods.csv with {len(read_loop_pods_df)} rows and {len(read_loop_pods_df.columns)} columns")


def main():
    parser = argparse.ArgumentParser(description='Plot MicroView benchmark results')
    parser.add_argument('--force', action='store_true', help='Force download even if files exist locally')
    parser.add_argument('--download', "-d", action='store_true', default=False, help='Skip downloading results from remote machine')
    parser.add_argument('--input-path', "-i",type=str, help='Folder where to work')

    args = parser.parse_args()
    
    # override default local path if run from command line
    if args.input_path:
        global LOCAL_PATH
        LOCAL_PATH = args.input_path

    # Download results from remote machine (unless skipped)
    if args.download:
        ret = download_results(args.force)
        if not ret:
            print("No results downloaded, exiting.")
            return
    else:
        print("Skipping download of results from remote machine.")
    
    # Collect results
    print('')
    print('')
    to_dataframe()
    
    print("Results saved to CSV files.")

if __name__ == "__main__":
    main()