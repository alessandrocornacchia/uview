# Overview

This section contains the instructions to reproduce the micro-benchmarks of MicroView on IPU as described in Section 6.2 of the paper.

## Prerequisites
Make sure to follow the [Getting Started](README.md#-getting-started) guide to verify the setup is working correctly and basic functionalities of MicroView, including access to the IPU instance.

## Run the microbenchmarks (~10h)

An automation script will run `wrk` benchmarks with/without the Prometheus endpoint, varying the number of metrics and pods, and the classification model (threshold or ML-based).

### From host machine `mcnode28` via `tmux`

You run the experiments from `mcnode28`. This is the machine connected to the BlueField2 IPU.
Re-running the benchmarks should take around 10 hours of compute time. 

#### Using `tmux` (recommended)
Because the experiments take a long time to run, we recommend using `tmux` to avoid losing progress. You can detach from the `tmux` session with `Ctrl+b d` and re-attach later with `tmux attach -t uview`.

```bash
tmux new -t uview
conda activate uview
python tests/benchmarks/tput.py -o ./results/nsdi-aec
```

#### Example output

```
(uview) aec-nsdi-1@mcbf28$ python tests/benchmarks/tput.py -o ./results/aec-nsdi
MicroView Micro-Benchmarking
================================
This script will run wrk benchmarks with/without the Prometheus endpoint

=== RUNNING METRIC COUNT BENCHMARK ===
**************************************************
EXPERIMENT_LABEL: metric_16_read_loop_TH
EXPERIMENT_MODE: read_loop
EXPERIMENT_DURATION: 600
NUM_PODS: 8
NUM_METRICS: 16
CLASSIFICATION_MODEL: TH
DEFAULT_PAGE_SIZE: 1024
DEFAULT_RDMA_MR_SIZE: 1024
**************************************************
[07:56:18] Starting MicroView distributed system:
[07:56:18] - Local host: 172.18.0.39:5000
[07:56:18] - Microview metrics reader: mcbf28
[07:56:18] - Metrics generators: 8 with 16 metrics each
[07:56:18] - LMAP collectors: 8
[07:56:18] - Scraping interval: 0 seconds
[07:56:18] - RDMA device: mlx5_3
[07:56:18] - Logs directory: ./logs
[07:56:18] Conda environment already activated: uview
[07:56:18] Starting MicroView host agent...
[07:56:18] Host agent started with PID 3116364
[07:56:18] Waiting 5 seconds for host agent to initialize...
[07:56:23] Starting 8 metrics generators with 16 metrics each...
[07:56:23] Started generator 1 with PID 3116549
[07:56:24] Started generator 2 with PID 3116594
[07:56:25] Started generator 3 with PID 3116640
[07:56:26] Started generator 4 with PID 3116675
[07:56:27] Started generator 5 with PID 3116719
[07:56:28] Started generator 6 with PID 3116758
[07:56:29] Started generator 7 with PID 3116810
[07:56:30] Started generator 8 with PID 3116849
[07:56:31] Waiting 5 seconds for metrics to register...
[07:56:36] Starting MicroView NIC collector on remote machine...
[07:56:41] Remote NIC collector started with PID 983924

=================================================================================
[07:56:41] 🎉 All components started:
[07:56:41] - 📃 Host agent logs in ./logs/host.log
[07:56:41] - 📃 Metric generator logs in ./logs/generator_*.log
[07:56:41] - 📃 NIC agents logs on mcbf28:./uview/logs/microview_collector.log

[07:56:41] Running for 600 seconds...
```

### Edit experiment settings
Should you tweak any parameters, you can edit directly the variables in the script `tests/benchmarks/tput.py`.
The script is a quick and dirty experiment runner which exports env variables then read by `run.sh` to start the distributed system. You can check the code for more details.

## Plot Fig.5 (~5 minutes)
Once the experiments have finished:
* Double-check that environment variables defined in `plot/run.sh` are correct and point to the right `uview` directories both in `mcnode28` and `mcbf28`.
* Run the plotting script:

```bash
cd plot
./run.sh
```

#### Expected output

The script will:
* download the measurement taken in the IPU to local path (default is `results/aec-nsdi/`)
* plot figure 5a and 5b as `tput_vs_metrics.png` and `tput_vs_pods.png` in the same directory under `figures`

You can change the output directories by setting the `LOCAL_PATH` environment variable in `run.sh`. 
