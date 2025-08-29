import os
from prometheus_api_client import PrometheusConnect
import requests
import json
import yaml
import argparse
from prometheus_api_client.utils import parse_datetime
from utils import make_path
from utils import write_metrics_dataset, build_metrics_dataframe
import fnmatch
import datetime as dt
import dateutil
from utils import parse_timeframe

"""
This script downloads metrics from prometheus and stores them in a csv file
Pod can be specified as input parameter, as well as partitioning of the dataset
between test and training set.

For counters the irate function is used, for gauges the rate function is used.
Histograms not used at the moment.

The script persists input parameters (e.g., dataset partitioning) 
to a yaml file, in the same dataset directory.

"""

parser = argparse.ArgumentParser()
parser.add_argument("--endpoint", "-e", type=str, help="Prometheus endpoint", required=True)
parser.add_argument("--config", "-c", type=str, help="Path to config", default="./metric_config.yaml")
parser.add_argument("--start-time", type=str, help="Query start time")
parser.add_argument("--end-time", type=str, help="Query end time")
parser.add_argument("--duration", "-d", type=int, help="Duration in minutes", default=None)
parser.add_argument("--service", "-s", type=str, help="Pod name", required=True)
parser.add_argument("--directory", 
                    "-D", 
                    type=str, 
                    help="Metric database directory", 
                    default="/data/scratch/cornaca/datasets/metrics")
parser.add_argument("--metrics-time-resolution", 
                    "-r", 
                    type=int, 
                    help="Desired resolution [seconds], i.e., time interval between two consecutive samples that we want in the output time series", 
                    default=30)

#argv = ["-e", "2023-06-30 15:25:00 UTC+2", "-d", "2", "-p", "frontend"]
args = parser.parse_args()

PROMETHEUS_ENDPOINT = f'http://{args.endpoint}'
#JAEGER_SERVICES_ENDPOINT = "http://172.18.0.28:32688/jaeger/api/services"

prom = PrometheusConnect(
    url = PROMETHEUS_ENDPOINT,
    headers= {'Host': args.endpoint.split(':')[0]},
    disable_ssl=True)

# Get the list of all the metrics
metric_names = prom.all_metrics()
print('\n\n== Connected to Prometheus DB. Total metrics available:', len(metric_names))

# Get metric types (API is experimental)
r = requests.get(f'{PROMETHEUS_ENDPOINT}/api/v1/metadata')
status = json.loads(r.text)['status']
metric_types = json.loads(r.text)['data']

start_time, end_time = parse_timeframe(args.start_time, args.end_time, args.duration)

# read configuration file
with open(args.config, 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

#== time series configuration
# prometheus scraping interval, based on that, later we compute the time window range for irate and rate
SCRAPING=config['global']['scrapingIntervalSeconds'] 
# desired resolution, i.e., time interval between two consecutive samples that we want in the output time series
STEP_SIZE=args.metrics_time_resolution
#== 

#== metrics family to query for
cAdvisor = 'cAdvisor' in config
kube_state_metrics = 'kube' in config
redis_metrics = 'redis' in config
histograms = bool(config['global']['histograms'])
#==

if not histograms:
    metric_names = list(filter(lambda m: 'bucket' not in m, metric_names))

P=args.service # extract prometheus metrics for this service 

queries = []

if cAdvisor:
    container_metrics = fnmatch.filter(metric_names, 'container_*')
    for m in config['cAdvisor']['blacklist']['metrics']:
        container_metrics.remove(m)

    for m in container_metrics:
        type = metric_types[m][0]['type'] if m in metric_types else 'counter'
        q = "%s{%s=~'.*%s.*'}" % (m, config['global']['service_label'], P)
        if type == 'counter':
            # recommended by prometheus doc averaging over at least 4x scraping interval
            q = f'rate({q}[{4*SCRAPING}s])' 
        
        # when many replicas of the same kind, aggregate using function specified here
        # not meaningful now
        #q = f"{config['cAdvisor']['aggFunction']}({q}) by (image, container)"
        queries.append(q)


if kube_state_metrics:
    kube_metrics = fnmatch.filter(metric_names, 'kube_*')
    if 'whitelist' in config['kube']:
        if 'names' in config['kube']['whitelist']:
            raise NotImplementedError('Not implemented yet')
        for q in config['kube']['whitelist']['queries']:
            if 'pod=' in q:
                q = q % P
            queries.append(q)


if redis_metrics and 'redis' in P:  
    if 'whitelist' in config['redis']:
        for q in config['redis']['whitelist']['queries']:
            if '%s' in q:
                q = q % f'{2*SCRAPING}s'
            print(q)
            queries.append(q)

# query prometheus API
print(f'== Running {len(queries)} queries for service {P}, start time: {start_time}, end time: {end_time}')
res, metric_descs = build_metrics_dataframe(prom, 
                                            start_time, 
                                            end_time, 
                                            STEP_SIZE, 
                                            queries, 
                                            verbose=True)
print(f'==> Downloaded metrics for {P}, dataset size: {res.shape}')

if len(res) == 0:
    print('No data downloaded. Exiting')
    exit(0)

# pad NaN observations if any
res = res.fillna(0)

# Set local time
dti = res.index.tz_localize('UTC').tz_convert(os.getenv('UTC_OFFSET_ZONE', 'Asia/Riyadh'))    #dateutil.tz.tzlocal()
res.set_index(dti, inplace=True)

# Write to file system metrics
path = make_path(args.directory, service=P)
write_metrics_dataset(path, res, metric_descs, filetail='')

# ..  and corresponding query configuration
path = make_path(args.directory)
args = vars(args)

with open(path + '/args.yaml', 'w') as f:
    yaml.dump(args, f)
with open(path + '/metric_types.json', 'w') as f:
    json.dump(metric_types, f)


