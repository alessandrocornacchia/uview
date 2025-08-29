#!/bin/bash

########################################################################
#             MicroView Distributed Deployment Script
# Runs host and generators on local machine, collector on remote machine
########################################################################

set -e  # Exit on error

# Default configuration (can be overridden by environment variables)
LOCAL_HOST=${LOCAL_HOST:-"0.0.0.0"}
LOCAL_PORT=${LOCAL_PORT:-5000}
LOCAL_PUBLIC_IP=${LOCAL_PUBLIC_IP:-$(hostname -I | awk '{print $1}')}  # Automatically get local IP
REMOTE_HOST=${REMOTE_HOST:-"ubuntu@192.168.100.2"}  # Change this to your remote machine
PROMETHEUS_PORT=${PROMETHEUS_PORT:-8000}


NUM_METRICS=${NUM_METRICS:-64}  # Number of metrics per pod
NUM_PODS=${NUM_PODS:-1}         # Number of pods 
NUM_LMAPS=${NUM_LMAPS:-1}       # Number of LMAP collectors
UVIEW_SCRAPING_INTERVAL=${UVIEW_SCRAPING_INTERVAL:-1}  # Interval for scraping metrics
CLASSIFICATION_MODEL=${CLASSIFICATION_MODEL:-"FD"}  # Model for classification see microview-nic.py -h for supported models

DEBUG=${DEBUG:-true}
LOGS_DIR=${LOGS_DIR:-"./logs"}
IPU_RDMA_DEVICE=${IPU_RDMA_DEVICE:-"mlx5_3"}
IPU_RDMA_IB_PORT=${IPU_RDMA_IB_PORT:-1}
IPU_RDMA_GID=${IPU_RDMA_GID:-1}
WAIT_TIME=${WAIT_TIME:-5} # time to wait before starting apps

# time to wait before killing the remote collector (useful if SmartNIC becomes not responsive)
# TODO
WATCHDOG_TIMER=${WATCHDOG_TIMER:-600} 

MYUSER=${MYUSER:-$(whoami)}
CONDA_ENV_NAME=${CONDA_ENV_NAME:-"uview"}  # Conda environment name
 
# Experiment mode: either "prometheus", "read_loop" or "setup"
EXPERIMENT_MODE=${EXPERIMENT_MODE:-"read_loop"}
# This will be used to organize files (logs, results, etc. ) in the remote machine if non empty
EXPERIMENT_LABEL=${EXPERIMENT_LABEL:-""}
# Duration of the experiment in seconds (0 for infinite until user stops)
EXPERIMENT_DURATION=${EXPERIMENT_DURATION:-0}

RESULT_DIR=${RESULT_DIR:-"./results"}
# Project folder on IPU
ROOT_DIR=${ROOT_DIR:-$(basename "$(pwd)")}

# Create logs directory if it doesn't exist
mkdir -p $LOGS_DIR

LOCAL_RUN=0

if [[ $REMOTE_HOST == "localhost" || $REMOTE_HOST == "" || $REMOTE_HOST == "0.0.0.0" ]] ; then
  LOCAL_RUN=1
fi


# ---------- functions ----------

# Rename statistics files on remote machine if EXPERIMENT_LABEL is non empty
handle_results() {
  
  # having a non empty label means we want to store results of this run in a specific folder
  if [ -n "$EXPERIMENT_LABEL" ]; then

    log "Renaming statistics files for experiment: $EXPERIMENT_LABEL"

    if [[ $LOCAL_RUN -eq 1 ]]; then
        # Move files locally
        mkdir -p $RESULT_DIR/$EXPERIMENT_LABEL
        rm -rf $RESULT_DIR/$EXPERIMENT_LABEL/*
        mv ./stats_*.csv $RESULT_DIR/$EXPERIMENT_LABEL/
        mv ./logs/microview_collector.log $RESULT_DIR/$EXPERIMENT_LABEL/
        log "Statistics files moved to $RESULT_DIR/$EXPERIMENT_LABEL/"
    else
        # do that on ssh      
        ssh $REMOTE_HOST "\
        cd $ROOT_DIR/ \
        && mkdir -p $RESULT_DIR/$EXPERIMENT_LABEL \
        && rm -rf $RESULT_DIR/$EXPERIMENT_LABEL/* \
        && mv ./stats_*.csv $RESULT_DIR/$EXPERIMENT_LABEL/ \
        && mv ./logs/microview_collector.log $RESULT_DIR/$EXPERIMENT_LABEL/ \
        && echo \"Statistics files moved to $RESULT_DIR/$EXPERIMENT_LABEL/\" 
        "
      fi
  
  fi
}

# Log function with timestamp
log() {
  echo "[$(date +%T)] $1" | tee -a "${LOGS_DIR}/main.log"
}

interrupted_by_user() {
  echo ""
  log "⚠️ Interrupted by user, cleaning up..."
  cleanup "1"
  exit 1
}


# Clean up function
cleanup() {
  
  local interrupted=${1:-0} 

  log "Forwarding signal to all processes..."
  
  # Send SIGTERM first to allow graceful cleanup
  [[ -n $HOST_PID ]] && kill -TERM $HOST_PID 2>/dev/null || true
  for pid in "${CLIENT_PIDS[@]}"; do
    kill -TERM $pid 2>/dev/null || true
  done
  
  if [[ $LOCAL_RUN -eq 1 ]]; then
    # If running locally, kill the collector process
    [[ -n $MICROVIEW_READER_PID ]] && kill -TERM $MICROVIEW_READER_PID 2>/dev/null || true
  else
    # If running remotely
    [[ -n $MICROVIEW_READER_PID ]] && ssh $REMOTE_HOST "kill -TERM $MICROVIEW_READER_PID" 2>/dev/null || true
  fi
  
  # Wait for microview reader processes to terminate, loop until process ID is found alive
  if [[ $LOCAL_RUN -eq 1 ]]; then
    # If running locally
    while ps -p $MICROVIEW_READER_PID > /dev/null; do
      sleep 1
    done
  else
    # If running remotely
    ssh $REMOTE_HOST "while ps -p $MICROVIEW_READER_PID > /dev/null; do sleep 1; done"
  fi
  
  # remove shared memory block if left open for any reason
  rm -f /dev/shm/microview

  # if the process was not interrupted by user, handle results
  if [[ $interrupted -eq 0 ]]; then
    handle_results
  fi
  
  log "✔️ All processes terminated"
  echo ""

}

# shortcut to activate conda env
_conda() {
  if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "Activating conda environment: $CONDA_ENV_NAME"
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate $CONDA_ENV_NAME
  else
    log "Conda environment already activated: $CONDA_DEFAULT_ENV"
  fi
}


# Run wrk benchmark that scrapes Prometheus endpoint
run_wrk_benchmark() {
  local result_dir="$RESULT_DIR"
  local target_url
  local benchmark_duration="$EXPERIMENT_DURATION"
  
  if [[ $LOCAL_RUN -eq 1 ]]; then
    target_url="http://localhost:$PROMETHEUS_PORT/metrics"
  else
    target_url="http://10.200.0.52:$PROMETHEUS_PORT/metrics"
  fi
  
  # Create results directory using experiment label if provided
  if [ -n "$EXPERIMENT_LABEL" ]; then
    result_dir="$RESULT_DIR/$EXPERIMENT_LABEL"
  fi
  mkdir -p "$result_dir"
  
  # Run the benchmark
  log "Running wrk benchmark against $target_url"
  log "Duration: $benchmark_duration"
  
  wrk -d"$benchmark_duration" -t1 -c1 --latency "$target_url" > "$result_dir/wrk_output.txt"
  
  # Display summary
  log "Benchmark complete. Results saved to $result_dir/wrk_output.txt"
  log "Summary:"
  grep "Requests/sec\|Latency" "$result_dir/wrk_output.txt" | sed 's/^/  /'
}
# ---------- functions ----------



# Set up trap
trap interrupted_by_user INT TERM

log "Starting MicroView distributed system:"
log "- Local host: $LOCAL_PUBLIC_IP:$LOCAL_PORT"
log "- Microview metrics reader: $REMOTE_HOST"
log "- Metrics generators: $NUM_PODS with $NUM_METRICS metrics each"
log "- LMAP collectors: $NUM_LMAPS"
log "- Scraping interval: $UVIEW_SCRAPING_INTERVAL seconds"
log "- RDMA device: $IPU_RDMA_DEVICE"
log "- Logs directory: $LOGS_DIR"


# Step 0: Activate conda environment
_conda

# 1. Start host agent on local machine
log "Starting MicroView host agent..."

python microview-host.py --rdma-queues $NUM_LMAPS --host $LOCAL_HOST --port $LOCAL_PORT $([ "$DEBUG" = true ] && echo "--debug") &> "${LOGS_DIR}/host.log" &
HOST_PID=$!
log "Host agent started with PID $HOST_PID"



# Wait for host agent to initialize
log "Waiting $WAIT_TIME seconds for host agent to initialize..."
sleep $WAIT_TIME



# 2. Start metrics generators on local machine
log "Starting $NUM_PODS metrics generators with $NUM_METRICS metrics each..."
CLIENT_PIDS=()
for i in $(seq 1 $NUM_PODS); do
  python libmicroview.py --num-metrics $NUM_METRICS --update-metrics $([ "$DEBUG" = true ] && echo "--debug") > "${LOGS_DIR}/generator_${i}.log" 2>&1 &
  CLIENT_PID=$!
  CLIENT_PIDS+=($CLIENT_PID)
  log "Started generator $i with PID $CLIENT_PID"
  sleep 1  # Add a small delay between starting each generator
done



# Wait for metrics to be registered
log "Waiting $WAIT_TIME seconds for metrics to register..."
sleep $WAIT_TIME


# 3. Start collector on remote machine via SSH
log "Starting MicroView NIC collector on remote machine..."

# if remote host is localhost, just run the script locally
if [[ $LOCAL_RUN -eq 1 ]]; then
  
    log "Remote host is localhost, running collector locally..."
    
    python microview-nic.py --control-plane $REMOTE_HOST:$LOCAL_PORT \
    --test $EXPERIMENT_MODE \
    $([ "$DEBUG" = true ] && echo "--debug") \
    --lmap $NUM_LMAPS \
    -m $CLASSIFICATION_MODEL \
    -s $UVIEW_SCRAPING_INTERVAL &> ./logs/microview_collector.log &
    
    MICROVIEW_READER_PID=$!
    log "Local collector started with PID $MICROVIEW_READER_PID"
  
else
    # Create the remote script using heredoc
    cat > "/tmp/remote_script.sh" << EOF
cd $ROOT_DIR
# uncomment below for development purposes to avoid copy & paste
# git pull
if [ ! -d "logs" ]; then mkdir logs ; fi
conda activate $CONDA_ENV_NAME
python microview-nic.py \\
    -c $LOCAL_PUBLIC_IP:$LOCAL_PORT \\
    -l $NUM_LMAPS \\
    -d $IPU_RDMA_DEVICE \\
    --gid $IPU_RDMA_GID \\
    --ib-port $IPU_RDMA_IB_PORT \\
    -s $UVIEW_SCRAPING_INTERVAL \\
    -m $CLASSIFICATION_MODEL \\
    --test $EXPERIMENT_MODE \\
    $([ "$DEBUG" = true ] && echo "--debug") &> ./logs/microview_collector.log &
MICROVIEW_COLLECTOR_PID=\$!

# keep this as last line: pid is needed to kill the process later
# verify the script is running with the right PID, if not something went wrong echo PID -1
ps -p \$MICROVIEW_COLLECTOR_PID > /dev/null && echo \$MICROVIEW_COLLECTOR_PID || echo -1
EOF
    
    
    
    # Execute the script on the remote machine, and store the PID to kill later
    ssh $REMOTE_HOST bash -ls < /tmp/remote_script.sh > "${LOGS_DIR}/.remote_pid.txt"
    # store in file to kill later at sigterm
    MICROVIEW_READER_PID=$(tail -n 1 "${LOGS_DIR}/.remote_pid.txt")
    if [[ $MICROVIEW_READER_PID -eq -1 ]]; then
      log "❌ Error: Failed to start remote collector. Please check the logs at ${LOGS_DIR}/.remote_pid.txt and on the remote machine."
      exit 1
    fi
    log "Remote NIC collector started with PID $MICROVIEW_READER_PID"
fi

# here success!
echo ""
echo "================================================================================="
log "🎉 All components started:"
log "- 📃 Host agent logs in ${LOGS_DIR}/host.log"
log "- 📃 Metric generator logs in ${LOGS_DIR}/generator_*.log"
log "- 📃 NIC agents logs on $REMOTE_HOST:./$ROOT_DIR/logs/microview_collector.log"
if [[ $EXPERIMENT_MODE == "prometheus" ]]; then
  log "- Prometheus metrics available at http://10.200.0.52:$PROMETHEUS_PORT/metrics"
fi
echo ""


# Three run mode:
# 1. Run promethues benchmark
# 2. the specified duration is reached
# 3. Keep script running until user interrupts
if [[ $EXPERIMENT_MODE == "prometheus" ]]; then
  log "Running in Prometheus benchmark mode"
  
  # Wait for system to stabilize
  STABILIZE_TIME=${STABILIZE_TIME:-10}
  log "Waiting $STABILIZE_TIME seconds for system to stabilize..."
  sleep $STABILIZE_TIME
  
  # Run the benchmark
  run_wrk_benchmark
  
  # Clean up after benchmark is complete
  cleanup
elif [ $EXPERIMENT_DURATION -gt 0 ]; then
  log "Running for $EXPERIMENT_DURATION seconds..."
  echo ""
  sleep $EXPERIMENT_DURATION
  cleanup
else
  log "Press Ctrl+C to stop"
  echo "================================================================================="
  echo ""
  tail -f "${LOGS_DIR}/host.log" #"$([ "$LOCAL_RUN" -eq 1 ] && echo "${LOGS_DIR}/microview_collector.log")"
  # here cleanup is called by the trap
fi
  