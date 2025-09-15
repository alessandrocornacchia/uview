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
parser.add_argument("--end", "-e", type=str, help="End time", required=True)
parser.add_argument("--config", "-c", type=str, help="Path to config", default="./metric_config.yaml")
parser.add_argument("--train-start", type=str, help="Training start time", required=True)
parser.add_argument("--train-end", type=str, help="Training end time", required=True)
parser.add_argument("--test-start", type=str, help="Test start time", required=True)
parser.add_argument("--test-end", type=str, help="Test end time", required=True)
parser.add_argument("--duration", "-d", type=int, help="Duration in minutes", required=True)
parser.add_argument("--pod", "-p", type=str, help="Pod name", required=True)
parser.add_argument("--directory", "-D", type=str, help="Metric database directory", default="/data/scratch/cornaca/datasets/metrics")

#argv = ["-e", "2023-06-30 15:25:00 UTC+2", "-d", "2", "-p", "frontend"]
args = parser.parse_args()

PROMETHEUS_ENDPOINT = 'http://prometheus.172.18.0.28.nip.io:31898'
#JAEGER_SERVICES_ENDPOINT = "http://172.18.0.28:32688/jaeger/api/services"

prom = PrometheusConnect(
    url = PROMETHEUS_ENDPOINT,
    headers= {'Host': 'prometheus.172.18.0.28.nip.io'},
    disable_ssl=True)

# Get the list of all the metrics
metric_names = prom.all_metrics()
#print('Total metrics available:', len(metric_names))

# Get metric types (API is experimental)
r = requests.get(f'{PROMETHEUS_ENDPOINT}/api/v1/metadata')
status = json.loads(r.text)['status']
metric_types = json.loads(r.text)['data']

# time intervals (do not specify timezone offset as UTC+2, or do it with the syntax +02:00)
end_time = parse_datetime(args.end)
start_time = end_time - dt.timedelta(minutes=args.duration)
train_start_time = args.train_start
train_end_time = args.train_end
assert parse_datetime(train_start_time) <= parse_datetime(train_end_time)
test_start_time = args.test_start
test_end_time = args.test_end
assert parse_datetime(test_start_time) <= parse_datetime(test_end_time)

# exclude metrics that are not of interest
with open(args.config, 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

istio = bool(config['metrics']['istio'])
envoy = bool(config['metrics']['envoy'])
cAdvisor = bool(config['metrics']['cAdvisor']['enable'])
kube_state_metrics = bool(config['metrics']['kube'])
redis_metrics = bool(config['metrics']['redis'])
histograms = bool(config['metrics']['histograms'])

if not histograms:
    metric_names = list(filter(lambda m: 'bucket' not in m, metric_names))

# service list
P=args.pod # extract prometheus metrics for this pod 
# prometheus scraping interval, based on that we compute the time window range for irate and rate
SCRAPING=config['metrics']['scrapingIntervalSeconds'] 
# this is the resolution, i.e., the time interval between two consecutive samples
STEP_SIZE=1

queries = []

# create a feature for each istio service mesh metric and pair of communicating microservices with POD
if istio:
    istio_metrics = fnmatch.filter(metric_names, 'istio_*')
    # retrieve service names (exclude loadgenerator and otelcollector)
    _, desc = build_metrics_dataframe(prom, 
                            start_time,
                            end_time, 
                            1, 
                            ['count(up{namespace=\'' + config['namespace'] + '\'}) by (app)'], 
                            verbose=False)
    
    SERVICES = []
    for x in desc:
        if 'app' in x:
            SERVICES.append(x['app'])

    # remove unwanted services
    for bs in config['blacklist']['services']:
        try:
            SERVICES.remove(bs)
        except:
            pass

    print('Scraping from', SERVICES)
    
    for m in istio_metrics:
        type = metric_types[m][0]['type'] if m in metric_types else 'counter'
        for peer in SERVICES:
            if 'agent' not in m:
                q = '%s{pod=~\'%s.*\', destination_app=\'%s\'}' % (m, P, peer)
                if type == 'counter':
                    q = f'irate({q}[{2*SCRAPING}s])'
                    #'irate(%s{pod=~\'%s.*\', destination_app=\'%s\', source_app!=\'loadgenerator\'}[%ds])' % (m, P, peer, 2*SCRAPING)
                queries.append(q)

if cAdvisor:
    container_metrics = fnmatch.filter(metric_names, 'container_*')
    for m in config['blacklist']['cAdvisor']:
        container_metrics.remove(m)

    for m in container_metrics:
        type = metric_types[m][0]['type'] if m in metric_types else 'counter'
        q = "%s{pod=~'.*%s.*', container=~'%s'}" % (m, P, config['metrics']['cAdvisor']['containerLabel'])
        if type == 'counter':
            q = f'rate({q}[{4*SCRAPING}s])'
        
        # when many pods are available, take the max value (fills zeros...)
        q = f"{config['metrics']['cAdvisor']['aggFunction']}({q}) by (image, container)"
        queries.append(q)

if envoy:
    envoy_metrics = fnmatch.filter(metric_names, 'envoy_*')
    for m in envoy_metrics:
        type = metric_types[m][0]['type'] if m in metric_types else 'counter'
        q = "%s{app=~'.*%s.*'}" % (m, P)
        if type == 'counter':
            q = f'rate({q}[{4*SCRAPING}s])'
        queries.append(q)

if kube_state_metrics:
    kube_metrics = fnmatch.filter(metric_names, 'kube_*')
    if 'kube' in config['whitelist']:
        if 'names' in config['whitelist']['kube']:
            raise NotImplementedError('Not implemented yet')
        for q in config['whitelist']['kube']['queries']:
            if 'pod=' in q:
                q = q % P
            queries.append(q)

# TODO we filter here so that only redis pod contains redis metrics, find better solution
if redis_metrics and 'redis' in P:  
    if 'redis' in config['whitelist']:
        for q in config['whitelist']['redis']['queries']:
            if '%s' in q:
                q = q % f'{2*SCRAPING}s'
            print(q)
            queries.append(q)

# query prometheus API
res, metric_descs = build_metrics_dataframe(prom, start_time, end_time, STEP_SIZE, queries, verbose=False)
print(f'==> Downloaded metrics for {P}, dataset size: {res.shape}')

# pad NaN observations if any
res = res.fillna(0)

# Set local time
dti = res.index.tz_localize('UTC').tz_convert('Asia/Riyadh')    #dateutil.tz.tzlocal()
res.set_index(dti, inplace=True)

# TODO would be easier to support collecting training and test data independently
# but then it's missing piece of code that asserts that the same metrics are collected
# and in the same order -> for now we only support this methodology where we collect
# both of them at once
df_train = res.loc[train_start_time:train_end_time]
df_test = res.loc[test_start_time:test_end_time]

# Write to file system metrics and parameters
path = make_path(start_time, end_time, rootdir=args.directory, service=P)
args = vars(args)
args['trainsize'] = str(df_train.shape)
args['testsize'] = str(df_test.shape)
with open(path + 'args.yaml', 'w') as f:
    yaml.dump(args, f)
with open(path + 'metric_types.json', 'w') as f:
    json.dump(metric_types, f)
write_metrics_dataset(path, df_train, metric_descs, filetail='_train')
write_metrics_dataset(path, df_test, metric_descs, filetail='_test')

# NodeExporter metrics
# if nodeExporter:
# NODE="mcnode18" # node exporter metrics for this node
# node_metrics = fnmatch.filter(metric_names, 'node_*')
# for m in node_metrics:
#     category = '_'.join(m.split('_')[:2])
#     if category not in available_queries.keys():
#         available_queries[category] = []
#     available_queries[category].append(q)
#     q = "rate(%s{node='mcnode18'}[30s])" % m
