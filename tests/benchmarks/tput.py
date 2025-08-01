import argparse
import sys
import os
import time

TIME_DURATION = 600
METRIC_SIZE_BYTES = 64
IPU_CORES = 8
IPU_ADDR = "ubuntu@192.168.100.2"
# reader_host = "localhost"
reader_host = IPU_ADDR

# global to be quick, this will never be imported
parser = argparse.ArgumentParser(description="MicroView Benchmarking")
parser.add_argument("--results-dir", "-o", default="./results", 
                    help="Directory to store benchmark results (default: ./results)")
args = parser.parse_args()



#-------------------------------------------
# here we fix number of pods and we vary number of metrics
def run_benchmark_metrics(mode = "read_loop"):
    """Run benchmark with varying number of metrics per pod"""
    print("\n=== RUNNING METRIC COUNT BENCHMARK ===")

    nmetrics = [16, 64, 128, 256]
    models = ["TH", "FD", "VAE"]
    # nmetrics = [64]
    # models = ["VAE"]
    num_pods = 8

    for m in models:
        for n in nmetrics:

            os.environ["EXPERIMENT_LABEL"] = f"metric_{n}_{mode}_{m}"
            os.environ["NUM_METRICS"] = str(n)
            os.environ["CLASSIFICATION_MODEL"] = m
            
            page_size = n * METRIC_SIZE_BYTES
            
            # this way each pod has one page
            os.environ["DEFAULT_PAGE_SIZE"] = str(page_size)
            
            # each pod gets one MR -> different LMAPs will read different MRs
            os.environ["DEFAULT_RDMA_MR_SIZE"] = str(1 *page_size)  
            
            os.environ["UVIEW_SCRAPING_INTERVAL"] = "0"
            os.environ["REMOTE_HOST"] = reader_host
            os.environ["EXPERIMENT_DURATION"] = str(TIME_DURATION)
            os.environ["DEBUG"] = "false"
            os.environ["NUM_PODS"] = str(num_pods)

            # number of LMAPs is always at most the number of cores of the IPU
            os.environ["NUM_LMAPS"] = str(min(IPU_CORES, num_pods))

            if mode == "prometheus":
                os.environ["WRK_RESULT_DIR"] = args.results_dir
            
            os.environ["EXPERIMENT_MODE"] = mode

            print("*"*50)
            print(f"EXPERIMENT_LABEL: {os.environ['EXPERIMENT_LABEL']}")
            print(f"EXPERIMENT_MODE: {os.environ['EXPERIMENT_MODE']}")
            print(f"EXPERIMENT_DURATION: {os.environ['EXPERIMENT_DURATION']}")
            print(f"NUM_PODS: {os.environ['NUM_PODS']}")
            print(f"NUM_METRICS: {os.environ['NUM_METRICS']}")
            print(f"CLASSIFICATION_MODEL: {os.environ['CLASSIFICATION_MODEL']}")
            print(f"DEFAULT_PAGE_SIZE: {os.environ['DEFAULT_PAGE_SIZE']}")
            print(f"DEFAULT_RDMA_MR_SIZE: {os.environ['DEFAULT_RDMA_MR_SIZE']}")
            print("*"*50)
                
            # run sh script
            os.system("./run.sh")


#-------------------------------------------
# here we fix number of metrics and we vary number of pods

def run_benchmark_pods(mode = "read_loop"):
    """Run benchmark with varying number of pods"""
    print("\n=== RUNNING POD COUNT BENCHMARK ===")

    nmetrics = 64

    # multiple of 16, so that we can have 16 pages for 16 pods in 1 MR
    num_pods = [8, 16, 64, 128, 256]
    models = ["TH", "FD", "VAE"]
    
    for m in models:
        for p in num_pods:
            os.environ["NUM_PODS"] = str(p)
            os.environ["EXPERIMENT_LABEL"] = f"pods_{p}_{mode}_{m}"
            os.environ["NUM_METRICS"] = str(nmetrics)
            os.environ["CLASSIFICATION_MODEL"] = m
            
            page_size = nmetrics * METRIC_SIZE_BYTES
            
            # this way each pod has one page
            os.environ["DEFAULT_PAGE_SIZE"] = str(page_size)
            
            
            # p/IPU_CORE is the number of pods per core i.e., MR i.e., LMAP
            os.environ["DEFAULT_RDMA_MR_SIZE"] = str(int(p / IPU_CORES * page_size))  
            
            os.environ["UVIEW_SCRAPING_INTERVAL"] = "0"
            os.environ["REMOTE_HOST"] = reader_host
            os.environ["EXPERIMENT_DURATION"] = str(TIME_DURATION)
            os.environ["DEBUG"] = "false"

            # number of LMAPs is always at most the number of cores of the IPU
            os.environ["NUM_LMAPS"] = str(min(IPU_CORES, p))

            if mode == "prometheus":
                os.environ["WRK_RESULT_DIR"] = args.results_dir
            os.environ["EXPERIMENT_MODE"] = mode

            print("*"*50)
            print(f"EXPERIMENT_LABEL: {os.environ['EXPERIMENT_LABEL']}")
            print(f"EXPERIMENT_MODE: {os.environ['EXPERIMENT_MODE']}")
            print(f"EXPERIMENT_DURATION: {os.environ['EXPERIMENT_DURATION']}")
            print(f"NUM_PODS: {os.environ['NUM_PODS']}")
            print(f"NUM_METRICS: {os.environ['NUM_METRICS']}")
            print(f"CLASSIFICATION_MODEL: {os.environ['CLASSIFICATION_MODEL']}")
            print(f"DEFAULT_PAGE_SIZE: {os.environ['DEFAULT_PAGE_SIZE']}")
            print(f"DEFAULT_RDMA_MR_SIZE: {os.environ['DEFAULT_RDMA_MR_SIZE']}")
            print("*"*50)
                
            # run sh script
            os.system("./run.sh")

 



if __name__ == "__main__":
        
    print("MicroView Micro-Benchmarking")
    print("================================")
    print("This script will run wrk benchmarks with/without the Prometheus endpoint")
    
    # Check if wrk is installed
    if os.system("which wrk > /dev/null") != 0:
        print("Error: wrk is not installed. Please install it with: sudo apt-get install -y wrk")
        sys.exit(1)
    
    # Run benchmarks
    run_benchmark_metrics()
    time.sleep(60)
    
    run_benchmark_pods()
    time.sleep(60)
    
    run_benchmark_metrics(mode = "prometheus")
    time.sleep(60)
    
    run_benchmark_pods(mode = "prometheus")
    
    
    print("\nAll benchmarks completed. Results are in the results/ directory.")