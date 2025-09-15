# Distributed tracing with microservices benchmarks

## Overview

This guide provides instructions to reproduce the distributed tracing use-case of MicroView (Sec. 6.3 of the paper). 

We used two representative microservice applications in two different execution environments:
- `HotelReservation` application in Docker Compose
- `Online Boutique` application in Kubernetes 

As such, the guide is divided into two parts:
1. [Docker Compose setup](#1-docker-compose-setup)
2. [Kubernetes setup](#2-kubernetes-setup)

For the purpose of the artifact reproduction, we tried to unify the steps as much as possible. Specifically, we deployed a `orchestrator.py` script to automate the deployment, load generation, anomaly injection, and data collection steps across the two environments.

Below are the detailed steps for each part.

### Useful information
We use NFS to share storage between the nodes, you should have access to `/home/temp/$USER/uview` on all nodes involved in the experiment, should you need to modify any files.

## 1) Docker Compose setup

This part includes steps to:
* deploy microservices applications using [Blueprint](https://blueprint-uservices.github.io) benchmark suite (SOSP '23)
* generate a load of requests to the applications using a workload generator
* run failure injection with [FIRM](https://www.usenix.org/conference/osdi20/presentation/qiu) (OSDI '20) injector

### Testbed

We use two nodes for these experiments, with the following roles:
- `mcnode17` : microservice application
- `mcnode18` : workload generator


### Kick-the-tyres run (~3 minutes)

Deploy and run a short experiment to test everything is in order:

```bash
ssh mcnode17
conda activate uview
cd ~/uview/usecases/experiments
python orchestrator.py -c dsbhotel-test -e DSBHotel-quick --chaos --loadgen
```

Experiments are automated with `orchestrator.py`. Two parameters are required:
- `-c` : configuration to use, among those defined in `experiments/configs/`
- `-e` : experiment name, used to store experiments artifacts under `usecases/experiments/<name>`

In the example above, `dsbhotel-test` is a minimal configuration that runs a short test and will create a folder `usecases/experiments/DSBHotel-quick`.

If successful, after a couple of seconds, expected output is similar to:
```
[+] Running 18/18
 ✔ Container docker-recomd_db_ctr-1               Running                                                                                                             0.0s 
 ✔ Container docker-reserv_db_ctr-1               Running                                                                                                             0.0s 
 ✔ Container docker-search_service_container-1    Started                                                                                                            12.6s 
[2025-08-20 08:26:23] ✅ Application containers started successfully
[2025-08-20 08:26:23] 🔍 Starting monitoring containers...
[+] Running 2/2
 ✔ Container monitoring-prometheus-1  Started                                                                                                                         0.6s 
 ✔ Container monitoring-cadvisor-1    Running                                                                                                                         0.0s 
[2025-08-20 08:26:24] ✅ Monitoring containers started successfully
[2025-08-20 08:26:24] 🎉 Deployment completed successfully!

[2025-08-20 08:26:24] === DEPLOYMENT SUMMARY ===
[2025-08-20 08:26:24] Application: dsb_hotel
[2025-08-20 08:26:24] Wiring Spec: original
[2025-08-20 08:26:24] Build Directory: build/original
[2025-08-20 08:26:24] Application containers: Running
[2025-08-20 08:26:24] Monitoring containers: Running

[2025-08-20 08:26:24] Use 'docker compose ps' to check container status
[2025-08-20 08:26:24] Use 'docker compose logs -f' to follow application logs
[2025-08-20 08:26:24] Use 'docker compose down' to stop the application
Starting workload generator on mcnode18

=== LOAD GENERATOR ===
Starting async load generator for user requests. Running on: mcnode18.
./wrk_http -config=/home/temp/aec-nsdi-1/uview/usecases/experiments/configs/quick-test/dsb_hotel.json -outfile="/home/temp/aec-nsdi-1/uview/usecases/experiments/DSBHotel/traces/latency.csv" &> /home/temp/aec-nsdi-1/uview/usecases/experiments/DSBHotel/loadgen.log &

=== ANOMALY INJECTION ===
Running anomaly injector with command: /home/temp/$USER/uview/usecases/chaos-engineering/anomaly-injector/venv/bin/python /home/temp/$USER/uview/usecases/chaos-engineering/anomaly-injector/injector.py -c /home/temp/aec-nsdi-1/uview/usecases/experiments/DSBHotel/injector.yaml -o /home/temp/aec-nsdi-1/uview/usecases/experiments/DSBHotel/faults.csv
```

> [!IMPORTANT]
> Please note that the `orchestrator.py` script will deploy the Docker Compose containers on the same node where it is running. This is typically `mcnode17` in our setup.

### Run paper experiments (~3 hours)

To run the actual experiments, we recommend using a `tmux`. You can start a new session with:
```bash
tmux new -s uview
```

and re-attach to it later with:
```bash
tmux attach -t uview
```

To detach from the session, press `Ctrl+b` followed by `d`.

```
```bash
ssh mcnode17
tmux attach -t uview
conda activate uview
cd ~/uview/usecases/experiments
python orchestrator.py -c dsbhotel-long -e DSBHotel --chaos --loadgen
```

Note that `dsbhotel-long` is a configuration available under `usecases/experiments/configs/` that runs a 1-hour experiment with multiple anomalies injected.

## 2) Kubernetes setup

This will use a 3-node Kubernetes cluster. Verify the output of `kubectl get nodes` to see the nodes in the cluster.

```
aec-nsdi-1@mcnode17 $ kubectl get nodes 
NAME       STATUS   ROLES           AGE     VERSION
mcnode17   Ready    worker          3h55m   v1.28.2
mcnode18   Ready    control-plane   209d    v1.28.2
mcnode19   Ready    worker          209d    v1.28.2
```

The process is similar to the Docker Compose setup, with the difference that the workload generator is deployed as a pod in the cluster this time.

#### Run a quick test

```bash
ssh mcnode17
conda activate uview
cd ~/uview/usecases/experiments
python orchestrator.py -c online-boutique-test -e online-boutique --chaos
```

Notice that the `--loadgen` flag is not needed here because the orchestrator will not need to ssh into another node to start the load generator.

#### Reproduce longer workload

```bash
ssh mcnode17
conda activate uview
cd ~/uview/usecases/experiments
python orchestrator.py -c online-boutique-long -e online-boutique --chaos
```


### ⚠️ Note 
We tried to automate the Kubernetes setup by patching the `orchestrator.py` script to ease the reviewers task. However, please note that this is not the original way we ran the experiments in the paper and has not been battle-tested as much as the Docker Compose setup. Please reach out if you encounter any issues.

## Run MicroView analysis pipeline
After the workload finished, it's time to run MicroView to analyze the results.

**Sanity check** You can first run the analysis on a smaller dataset derived from the [kick-the-tyres](#kick-the-tyres-run-3-minutes) run above. This verifies that you can collect observability data, and run the sketch.

```bash
cd ~/uview/usecases/postprocessing
./run-uview.sh all DSBHotel-quick
```

The script ill collect traces, metrics, and logs from the deployed microservices application and store them in the `usecases/experiments/DSBHotel-quick` directory. 

#### Generated artifacts 

At this point, you should find the following artifacts:
- `traces/latency.csv`: latency traces collected by the workload generator
- `faults.csv`: ground truth of injected anomalies, with timestamps, types and affected services
- `anomalies.log`: failure injection log
- `loadgen.log`: logs of the load generator
- `injector.yaml`: configuration file used by the anomaly injector
- `<app name>.json`: configuration file used by the load generator
- `metrics`: directory containing Prometheus metrics collected from the application
- `jaeger`: directory containing Jaeger traces, with different sampling intervals (e.g., 1%, 10%, 100%)

In particular, verify that the following are created:
- `traces/*frontend*_sketch_sampled.csv.gz` : sampled traces using MicroView's sketching algorithm
- `metrics/best_config.csv` : metrics classification based on FD-Sketch with optimized per-service hyperparameters

Now you can run the full MicroView analysis pipeline on the full dataset.

```bash
cd ~/uview/usecases/postprocessing
./run-uview.sh all DSBHotel
```
