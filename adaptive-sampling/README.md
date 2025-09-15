# Adaptive Sampling

This folder contains code to reproduce Fig.8 of the paper.

## Overview

We provide the metrics recorded for an instance of a `redis-service` pod. Redis is a popular in-memory store, used as a database, cache, and message broker.

We chose redis as it our setup generates both container-level metrics (e.g., CPU, memory) and application-level metrics (e.g., Redis-specific) for it. 
Other services in Blueprint do not come with application-level metrics.

## Run experiment (~5 minutes)

The folder `artifacts/metrics` contains the metrics dataset for this experiment. 

The file `artifacts/metrics/column_desc_test.json` contains the Prometheus query used to collect every metric.

For running the sketch configuration used in the experiment, execute:
```bash
cd adaptive-sampling
python ./usecases/postprocessing/classify_pod_metrics.py --task dynamic_sampling -s redis-cart -l 25 -k 10 -th 99.9 -d ./adaptive-sampling/artifacts --learning-rate 0
```

You then obtain `artifacts/results` folder. 

## Plot results (~1 minute)

Run:
`python plot.py`
and look for the generated`png` plots in `adaptive-sampling` directory.
