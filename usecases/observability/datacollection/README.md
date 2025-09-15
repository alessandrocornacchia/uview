# Overview

This is a detailed guide that describes the client for traces and metrics collection.

#### Relevance and scope
You can ignore this README if you are just interested in the MicroView system and its evaluation. Refer to [Detailed Instructions](/README.md#-detailed-instructions) sections of the main [README](/README.md)


## :clock2:Traces collection

For trace collection we use the Jaeger HTTP API.

Use your preferred tool (`pipenv`, `conda`, `mamba`) to create a python environment and install the dependencies `datacollection/requirements.txt`.

The script `./jaeger_traces.py` will:
- connect to the jaeger HTTP API url
- dowload traces in the JSON format
- parse the JSON format and produce a more understandable CSV file containing 
    * start time of the trace
    * end time of the trace
    * flag indicating if HTTP/gRPC error codes are present
    * HTTP operation name
    * service chain traversed by the trace
- create a new folder under `../../datasets` with the new traces


### Example of how to run
Activate the python environment and run:
```
cd metrics-monitoring/datacollection

python ./jaeger_traces.py --service "unknown_service:search_service_process" -D ./../datasets --jaeger-endpoint "0.0.0.0:12349" download
```

If you want to specify the timeframe to query for, you can pass as command line arguments. The following will query for traces not older than 60 minutes with respect to `2024-07-12 10:00:00 CET time`.
```
python ./jaeger_traces.py --service "unknown_service:search_service_process" -D ./../datasets --jaeger-endpoint "0.0.0.0:12349" -e "2024-07-12 10:00:00 UTC$(TZ=Europe/Rome date +%:::z)" -d 60 download
```

#### Script
You may want to use `run-collect.sh` to automate this 


## :chart_with_downwards_trend: Metrics collection

For metrics, we use a similar approach to collect from Prometheus. The script `run_collect.sh` automates the process of:
- understanding running services for a given application
- executing the `prometheus-metrics.py` client

### Setting Prometheus and cAdvisor collection frequency

- Set the variable `HOUSEKEEPING_INTERVAL` in `docker/.env` file to a numeric value in seconds
- Check the parameters of `prometheus.yaml` configuration file

Have a look at it and set parameters you want
Also, you can available options of the Prometheus client with `python prometheus-metrics.py -h`. The Prometheus client:
-  reads which metrics to collect (or ignore) through a `.yaml` configuration file. Check `metrics_config.yaml` as a reference example. 
- collect metrics over a given timeframe you can specify via command line.


After running the metrics collection script you find in the directory you specified to the client:
- a CSV file where each column is a metric time-series
- the list of executed queries in a file `column_desc_train.json`. This is useful to associate which CSV columns correspond to which Promethues queries (see below)
- a `.yaml` file with the configuration used to collect the metrics

### Mapping dataset columns to Prometheus queries
You can use jq and grep to inspect the query name for a given CSV column. Columns have incremental names starting from `value_0`. 
You can run:

```
cat ./datasets/metrics/<dir name>/<service name>/column_desc_train.json | jq | grep -A 2 -B 2 "value_<your column>"
```