#%%
import yaml
import os
import argparse
import time
from prometheus_api_client.utils import parse_datetime, parse_timedelta
from datetime import timedelta
from prometheus_api_client import PrometheusConnect
from pytimeparse.timeparse import timeparse
import itertools

script_dir = os.path.dirname(os.path.realpath(__file__))

housekeeping_intervals = ['1s', '10s', '1m']
scraping_intervals = ['1s', '10s', '1m']
container_replicas = [1, 10, 100, 1000]

metrics = {
    "cpu_sys": 'container_cpu_system_seconds_total', 
    "cpu_user": 'container_cpu_user_seconds_total', 
    "cpu": 'container_cpu_usage_seconds_total',
    "net": 'container_network_transmit_bytes_total'
}

experiment_duration = '5m'
container_replicas = [1000]

# these can have more complex logic for kube, docker, etc.
def start_containers_cmd(sudo=False):
    cmd = "docker compose up -d"
    if sudo:
        cmd = "sudo " + cmd
    return cmd

def stop_containers_cmd(sudo=False):
    cmd = "docker compose down"
    if sudo:
        cmd = "sudo " + cmd
    return cmd


def tear_up():
    # start monitoring containers with force-recreate option
    r1 = os.system(f"sudo HOUSEKEEPING_INTERVAL={h} " 
                  + start_containers_cmd() 
                  + " --force-recreate cadvisor prometheus")
    
    # start replicas containers (can keep old containers if already present
    # to speed-up. i.e. don't use --force-recreate)
    r2 = os.system(start_containers_cmd() + " redis")
    return r1+r2



def tear_down():
    return os.system(stop_containers_cmd())


def deploy(h, s, c):
    print(f"== Running with housekeeping_interval={h}, scraping_interval={s}, container_replicas={c}")
    
    # customize yaml docker-compose config
    with open("docker-compose.yml", 'r') as stream:
        try:
            compose = yaml.safe_load(stream)
            compose['services']['redis']['deploy']['replicas'] = c
        except yaml.YAMLError as exc:
            print("Cannot read to docker-compose.yml")
            return 1

    with open("docker-compose.yml", 'w') as stream:
        try:
            yaml.dump(compose, stream)
        except yaml.YAMLError as exc:
            print("Cannot write to docker-compose.yml")
            return 1

   
    # customize promtheus config yaml
    with open("prometheus.yml", 'r+') as stream:
        try:
            prometheus = yaml.safe_load(stream)
            for config in prometheus['scrape_configs']:
                if config['job_name'] == 'cadvisor':
                    config['scrape_interval'] = s
                    break
        except yaml.YAMLError as exc:
            print("Cannot read from prometheus.yml")
            return 1
    
    with open("prometheus.yml", 'w') as stream:
        try:
            yaml.dump(prometheus, stream)
        except yaml.YAMLError as exc:
            print("Cannot write to prometheus.yml")
            return 1
    
    return tear_up()
    



def get_resource_usage(h, s, c):
    try:
        prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)
    except Exception as e:
        print("== Error connecting to prometheus")
        print(e)
        os.system(stop_containers_cmd())
        exit(1)

    start_time = parse_datetime(experiment_duration)
    end_time = parse_datetime("now")
    step = timeparse(s) # chunk size same as scraping rate
    window = str(4*timeparse(s)) + "s" # lookback window for rate computation

    print(f"== Experiment ended. Collecting data in the last {experiment_duration}. Step size: {s}")

    # collect cAdvisor resource usage data 
    measurments = dict()
    timestamps = None

    for metric, metric_query in metrics.items():

        # for each data point in the time series of the resource consumptions we collect, consider a lookback window of 4 scrapes
        # to compute the rate of change in the metric
        query = "rate(" + metric_query + "{container_label_com_docker_compose_service='cadvisor'}[" +  window  + "])"
        print(f"== Querying {query}")

        data = prom.custom_query_range(
            query,
            start_time=start_time,
            end_time=end_time,
            step=step
        )

        timestamps, v = zip(*data[0]['values'])
        measurments[metric] = v
        
    # write to file
    with open(f"{script_dir}/data/housekeeping{h}_scraping{s}_replicas{c}.csv", 'w') as f:
        f.write("time,{}\n".format(','.join(metrics.keys())))
        
        for i in range(len(timestamps)):
            f.write("{},{}\n".format(
                timestamps[i], 
                ','.join([str(measurments[m][i]) for m in metrics.keys()])))

    


#--- run the experiment for selected configurations

# keep this in outer loop so that for large number of container we create them only once and destroy at the very end
for c in container_replicas: 
    for h in reversed(housekeeping_intervals):
        for s in reversed(scraping_intervals):
            
            if timeparse(s) < timeparse(h):
                print(f"== Skipping housekeeping_interval={h} and scraping_interval={s} as scraping_interval < housekeeping_interval")
                continue

            r = deploy(h, s, c)

            if r != 0:
                print("== Error starting docker compose, skipping this experiment")
                os.system(stop_containers_cmd())
                continue

            print(f"== Experiment started. Sleeping for {experiment_duration}")
            time.sleep(timeparse(experiment_duration))

            get_resource_usage(h, s, c)

# TODO: ideally stop everything in case of error or at the very end (check what happens if you have 100 replicas then you ask for 10)
ret = tear_down()
if ret != 0:
    print("== Error stopping docker compose")
                
