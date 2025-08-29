import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.pyplot as plt
from sklearn import metrics
import requests
import datetime
from prometheus_api_client.utils import parse_datetime
import numpy as np
import re

def get_services(endpoint):
    """
    Returns list of all services
    """
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise err
        
    response = json.loads(response.text)
    services = response["data"]
    return services

def plot_metric(df, mid, metric_descs=None):
    """
    Plot a given metric (specified as column index)
    You can retrieve column index by looking into column description json file. 
    For example:
        cat <pod>_column_desc.json | jq | grep -A 2 'milliseconds_sum'
    """
    df.plot.line(y=f'value_{mid}' if mid>0 else 'value', marker='*')
    if metric_descs is not None:
        str = metric_descs[mid]['query']
        ylabel_ = re.search('\((.+)\{', str).group(1)
        plt.ylabel(ylabel_)
    plt.show()

def load_traces(filepath):
    """ Load traces using header file in same folder """
    dir = os.path.dirname(filepath)
    try:
        header = pd.read_csv(f'{dir}/header.csv').columns.values
    except:
        print('Header file not found, assuming default')
        header = ['traceID', 'duration-ms', 'startTime', 'endTime', 'rpcErrors', 'operation']
        
    traces = pd.read_csv(
        filepath, 
        compression='gzip',
        names=header)
    
    return traces

def preprocess_traces(traces):
    """ Reads csv file with traces and converts timestamps to datetime """
    print("Trace pre-processing, received traces", traces.head())
    traces['startTime'] = pd.to_datetime(
        traces['startTime'], 
        unit='us', 
        utc=True
    ).dt.tz_convert('Asia/Riyadh')
    traces['endTime'] = pd.to_datetime(
        traces['endTime'],
        unit='us',
        utc=True
    ).dt.tz_convert('Asia/Riyadh')
    traces = traces.sort_values(by='startTime').set_index('startTime')
    return traces


def compute_trace_statistics(dataset_filename, dir):
    
    all = preprocess_traces(load_traces(dataset_filename))

    print("Now keeping only training traces")
    df = filter_training_traces(all, f'{dir}/..')
    
    trace_stats = {
        'median' : df.groupby(by='operation')['duration-ms'].quantile(.5).to_frame('median'),
        '99.9th' : df.groupby(by='operation')['duration-ms'].quantile(.999).to_frame('99.9th'),
        '99th' : df.groupby(by='operation')['duration-ms'].quantile(.99).to_frame('99th'),
        '95th' : df.groupby(by='operation')['duration-ms'].quantile(.95).to_frame('95th'),
        'mean' : df.groupby(by='operation')['duration-ms'].mean().to_frame('mean'),
        '3-sigma': (df.groupby(by='operation')['duration-ms'].std() * 3 + df.groupby(by='operation')['duration-ms'].mean()).to_frame('3-sigma')
    }
    path = os.path.join(dir,'traces_999th.csv')
    trace_stats['99.9th'].to_csv(path)
    path = os.path.join(dir,'traces_99th.csv')
    trace_stats['99th'].to_csv(path)
    path = os.path.join(dir,'traces_95th.csv')
    trace_stats['95th'].to_csv(path)
    path = os.path.join(dir,'traces_median.csv')
    trace_stats['median'].to_csv(path)
    path = os.path.join(dir,'traces_mean.csv')
    trace_stats['mean'].to_csv(path)
    path = os.path.join(dir,'traces_3-sigma.csv')
    trace_stats['3-sigma'].to_csv(path)
    
    return trace_stats


def filter_training_traces(traces, experiment_dir):

    """
      read the first and last line from timestamps in data_train.csv in any of the metrics folders
      and uses that to filter traces collected during the same time interval
    """

    # obtain training timeframe by looking at first available metrics folder
    metrics_dir = os.listdir(f'{experiment_dir}/metrics')
    for d in metrics_dir:
        if os.path.isdir(f'{experiment_dir}/metrics/{d}'):
            if 'data_train.csv' in os.listdir(os.path.join(f'{experiment_dir}/metrics', d)):
                data_train = pd.read_csv(f'{experiment_dir}/metrics/{d}/data_train.csv', parse_dates=['timestamp'])
                break
    
    # keep only traces in this timeframe
    start = data_train['timestamp'].iloc[0]
    end = data_train['timestamp'].iloc[-1]
    print(start, end)
    return traces[start:end]

def get_training_dataset(traces, experiment_dir):
    """ Assumptions: 
    - training datasets starts at the end of test dataset 
    - experiment directory contains a file called faults.csv with anomalies
    """
    anomalies_path = f"{experiment_dir}/faults.csv"
    _, anomalies = label_anomalous_samples(pd.DataFrame(), anomalies_path)
    traces = traces[traces['operation'] != '/_healthz']
    return traces[anomalies[-1][1]:]


def label_anomalous_samples_from_file(interval_files, dataset, timezone='Asia/Riyadh'):
    """
    Labels samples as anomalous or not based on a given input file 
    containing pairs of kind <from>,<to> representing anomalous intervals
    """
    dfi = pd.read_csv(interval_files, parse_dates=['from', 'to'])
    dfi = dfi.applymap(lambda x: x.tz_localize(timezone))
    # drop samples time tagged within the interval
    to_label = []
    for index in dataset.index:
        for _, row in dfi.iterrows():
            if (index > row['from']) & (index < row['to']):
                to_label.append(index)
                break
    dataset['label'] = 0
    dataset.loc[to_label, 'label'] = 1
    return dataset


def label_anomalous_samples(df, anomalies, svc=None):
    """"
    Given a list of tuples containing anomalous intervals (or path to file)
    returns a dataframe with labeled samples 
    """
    df['label'] = 0
    if type(anomalies)==str:
        try:
            dfi = pd.read_csv(anomalies, parse_dates=['start', 'end'])
        except FileNotFoundError as e:
            print(f'Error reading file {anomalies}, make sure it exists')
            exit(1)
            
        # if service is provided, use only anomalies for that service
        if svc is not None:
            dfi = dfi[dfi['service'].str.contains(svc)]
        
        dfi = dfi[['start', 'end']]
        dfi['start'] = dfi['start'].dt.tz_convert('Asia/Riyadh')
        dfi['end'] = dfi['end'].dt.tz_convert('Asia/Riyadh')
        dfi = dfi.sort_values(by='start')
        anomalies = list(dfi[['start', 'end']].itertuples(index=False, name=None))
    for a in anomalies:
        df.loc[a[0]:a[1], 'label'] = 1
    return df, anomalies


def plot_score_distribution(scores, ascores=None, f=None):
    # plot anomaly score distribution
    plt.figure(figsize= (4,1.5), dpi=300)
    bins = np.linspace(0,1,50)

    value, bins, _ = plt.hist(
        scores['values'], 
        bins=bins, 
        density=True,
        facecolor='g', 
        alpha=0.75, 
        label=scores['key'])
    
    if ascores:
        value, bins, _ = plt.hist(
            ascores['values'], 
            np.linspace(0,1,20),
            density=True,
            facecolor='orange',
            alpha=0.75,
            label=ascores['key'])
            
    plt.xlabel('Anomaly Score')
    plt.ylabel('PDF')

    plt.legend(fontsize=6, loc='upper right')
    plt.grid(True)
    if f:
        mysavefig(f, bbox_inches='tight')
    else:
        plt.show()


# ROC curve
def plot_roc(labels, scores):

    fpr, tpr, thresholds = metrics.roc_curve(labels, scores, drop_intermediate=False)
    auc_ = metrics.auc(fpr, tpr)
   
    lw = 2
    plt.plot(
        fpr,
        tpr,
        color="darkorange",
        lw=lw
        #label="ROC curve (area = %0.2f)" % ,
    )
    plt.plot([0, 1], [0, 1], color="navy", lw=lw, linestyle="--")
    #plt.xlim([0.0, 1.0])
    #plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(f"AUC={auc_}")
    plt.legend(loc="lower right")
    plt.show()

    return thresholds


def plot_precision_recall(labels, scores, f = None):

    precision, recall, thresholds = metrics.precision_recall_curve(labels, scores)
    auc_ = metrics.auc(recall, precision)
    plt.figure()
    lw = 2
    plt.plot(
        recall,
        precision,
        color="darkorange",
        lw=lw,
        label="FDsketch"
    )
    
    no_skill = np.sum(labels) / len(labels)

    plt.axhline(y=no_skill, color="navy", lw=lw, label='no skill', linestyle="--")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title(f"AUC={auc_}")
    plt.legend(loc="lower right")
    if f:
        mysavefig(f, bbox_inches='tight')
        pd.DataFrame({
            'precision': precision, 
            'recall': recall,
            'thresholds': np.append(thresholds, np.Inf)}).to_csv(f+'.csv')
    else:
        plt.show()

    return thresholds

def mysavefig(f, verbose=True, **kwargs):
    if verbose:
        print(f'Saving to {f}')
    plt.savefig(f+'.png', **kwargs)
    plt.savefig(f+'.pdf', **kwargs)
    plt.close()


def chaos_timestamps_to_intervals(timestamp_file, outfile, duration_seconds=30):
    """
    From a file of the form <start anomaly>,<microservice affected>
    gets a file of tuples with anomalous intervals
    """
    df = pd.read_csv(
        timestamp_file, 
        parse_dates=['timestamp'])
    df['to'] = df['timestamp'] + datetime.timedelta(seconds=duration_seconds)
    df.sort_values('timestamp')[['timestamp', 'to']].to_csv(outfile, index=False)



def periodic_anomaly(start, end, every_seconds, duration_seconds, path):
    """
    Generates a file with anomalous intervals
    """
    intervals = []
    start = parse_datetime(start)
    end = parse_datetime(end)
    duration = datetime.timedelta(seconds=duration_seconds)
    every = datetime.timedelta(seconds=every_seconds)
    
    with open(path, 'w') as f:
        while start + duration < end:
            intervals.append((start, start+duration))
            print(f'{start},{start+duration}', file=f)
            start = start + every
    return intervals


def col_name_to_metric(columns, desc_file):
    """
    Reads column identifier from generic column name of kind value_ID
     and returns corresponding query describing the metric, by reading 
     description json at key ID
    """
    #file = ''.join(dataset_file.split('.')[:1] + ["_column_desc.json"])
    with open(desc_file, 'r') as f:
        desc = json.load(f)
    r = []
    for c in columns:
        try:
            id = int(c.split('_')[-1])
        except:
            id = 0
        r.append(desc[id]['query'])
    return r
