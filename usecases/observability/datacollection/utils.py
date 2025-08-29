import os
import pickle
import ijson
import gzip
import requests
import csv
import json
import random
import copy
import pandas as pd
from prometheus_api_client import MetricRangeDataFrame
from prometheus_api_client.utils import parse_datetime
import sys
import datetime
import click


def parse_timeframe(start, end, duration):
    if duration:
            if start:
                start_time = parse_datetime(start)
                end_time = start_time + datetime.timedelta(minutes=duration)
            else:
                start_time = None
            
            if end:
                end_time = parse_datetime(end)
                start_time = end_time - datetime.timedelta(minutes=duration)
            else:
                end_time = None
    else:
        try:
            start_time = parse_datetime(start)
            end_time = parse_datetime(end)
        except:
            print("Either duration or <start and end time> must be provided")
            sys.exit(1)
    if (start_time is None or end_time is None) or start_time >= end_time:
        print("Invalid time frame")
        sys.exit(1)

    print(f'==> Timeframe: {start_time} - {end_time}')
    return start_time, end_time



def stream_traces(f, out, compression=True, debug=False):
    """
    Stream traces from Jaeger API and write to CSV file. If debug is true, also return 
    list of traces. It implements a caching mechanism. For a given directory, it keeps
    track of which traceIDs have already been collected from previous services and
    skips them.

        f : file descriptor pointing to Jaeger endpoint or file with json
        out : output file
    """
    
    def openf(f, compression):
        if compression:
            return gzip.open(f, 'wt', compresslevel=9, newline='')
        return open(f, 'w', newline='')
    
    row = {}
    row["traceID"] = None #["traceID", "duration-ms", "startTime", "endTime", "rpcErrors", "operation"]
    row["duration-ms"] = None
    row["startTime"] = None
    row["endTime"] = None
    row["rpcErrors"] = None
    row["operation"] = None
    row["processes"] = None

    if os.path.exists(out):
        if not click.confirm(f'File {out} already exists. Overwrite?', default = True, show_default=True):
            print(f'\r==> 0 new written traces to {out}', end='', flush=True)
            return
        
    with openf(out, compression) as o:
        w = csv.writer(o)
        #w.writerow(row.keys())
        traces = ijson.items(f, 'data.item')
        i = 0
        tot = 0
        ret = []
        for t in traces:
            tot += 1
            i += 1
            if i%100==0:
                # update progress bar
                print(f'\r==> {i} written traces to {out}', end='', flush=True)
            spans = t['spans']
            endTrace = max([s['startTime'] + s['duration'] for s in spans])
            startTrace = min([s['startTime'] for s in spans])
            traceDuration = endTrace -startTrace
            hasErrors = False
            for si in range(len(spans)):
                if si == 0:
                    operationName = spans[si]['operationName']
                for tag in spans[si]['tags']:
                    if tag['key'] == 'error':
                        hasErrors = tag['value']
                        break
            
            processes = []
            for p in t['processes']:
                processes.append(t['processes'][p]['serviceName'])

            row["traceID"] = t["traceID"]
            row["duration-ms"] = traceDuration/1000 
            row["startTime"] = startTrace
            row["endTime"] = endTrace
            row["rpcErrors"] = hasErrors
            row["operation"] = operationName
            row['processes'] = ';'.join(set(processes)) # processes involved in this trace
            
            w.writerow(row.values())
            if debug:
                ret.append(copy.copy(row))
    
    print(f'\r==> {i}/{tot} written traces to {out}', end='', flush=True)
    
    with open(os.path.dirname(out) + '/header.csv', 'w') as ff:
        w = csv.writer(ff)
        w.writerow(row.keys())

    if debug:
       return ret


def get_available_services(jaeger_endpoint):
    """ use jaeger service endpoint to collect """
    raise NotImplementedError('Not implemented yet')

def get_traces(query_params, endpoint):
    """
    Returns list of all traces for a service
    Could be memory intensive
    """
    try:
        # Send the API request and extract the trace data
        if query_params["operation"]=="":
            query_params.pop("operation")
        print('==> Requesting traces to Jaeger API')
        response = requests.get(endpoint, params=query_params)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise err

    response = json.loads(response.text)
    traces = response["data"]
    return traces


def head_sampling(f, p, chunksize=10000):
    """
    Reads a (potentially large) CSV file and samples traces with probability p
    """
    print(f'==> Sampling traces in {f} with p={p}')
    header = True
    outfile = f'{f.split(".")[0]}_sampling_{p*100}x.csv.gz'
    if not os.path.exists(outfile):
        for chunk in pd.read_csv(f, compression='gzip', chunksize=chunksize):
            sampled = []
            for i in range(len(chunk)):
                if random.random() <= p:
                    sampled.append(chunk.index[i])
            chunk.loc[sampled].to_csv(outfile, 
                        mode='w' if header else 'a', 
                        header=header, 
                        index=False, 
                        compression='gzip')
            header = False


def write_metrics_dataset(path, dataset, columndesc, filetail=''):
    """
    Write metric dataset and its description locally to files
    """
    file = os.path.join(path, f'data{filetail}.csv')
    print("Writing metrics dataset to", file)
    dataset.to_csv(file, mode='w')
    # write metric description (same order as columns) to json file
    file = os.path.join(path, f'column_desc{filetail}.json')
    with open(file, 'w') as f:
        json.dump(columndesc, f)
    

def build_metrics_dataframe(prometheus_client, start_time, end_time, step, queries, verbose=True):
    """
    Queries prometheus API and constructs dataframe object and 
    associated metrics descriptions
    """
    metric_descs = []
    features = 0
    if len(queries) == 0:
        raise ValueError('No queries provided')
    
    for i in range(len(queries)):
        if verbose:
            print(queries[i])
        metric_query_range = prometheus_client.custom_query_range(
            queries[i],
            start_time=start_time,
            end_time=end_time,
            step=step
        )
        if verbose and len(metric_query_range) == 0:
            print('Empty query result for:', queries[i])
        for j in range(len(metric_query_range)):
            df = MetricRangeDataFrame(metric_query_range[j])
            if df['value'].isna().sum():
                print('Has NaNs:', j)
            if features >= 1:
                res = res.join(df[['value']], rsuffix=f'_{features}', how='outer')
            else:
                res = df[['value']]
            metric_query_range[j]['metric']['query'] = queries[i]
            metric_query_range[j]['metric']['key'] = features
            metric_descs.append(metric_query_range[j]['metric'])
            features = features + 1  
    return res, metric_descs


def make_path(directory, service=None):
    """
    Make path for storing metrics dataset: use environment 
    variable EXPERIMENT_ID, else create according to timerange
    """
    
    if service:
        directory = os.path.join(directory, service)
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory