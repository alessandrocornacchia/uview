#%%
import os, sys; 
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import pandas as pd
import matplotlib.pyplot as plt
from utils import load_traces, mysavefig, preprocess_traces, get_training_dataset, compute_trace_statistics
import seaborn as sns
from globals import *

#plt.style.use('seaborn')

################    parameters
#timerange = '202307181558-202307181658' # cpu
if 'DATASET_TIMEFRAME' not in globals():
    timerange = '14Sept0950' #'202312041030-202312041100' #'202308020913-202308021013'
    print(f'Timeframe not specified in cmdline, using {timerange}')
else:
    timerange = DATASET_TIMEFRAME
saveplot = False
download = False
################

if download:    # download now and don't read from file
    from datacollection.jaeger_traces import download
    from prometheus_api_client.utils import parse_datetime
    import datetime
    end_time = parse_datetime('2023-08-01 15:52:00 UTC+2')
    start_time = end_time - datetime.timedelta(minutes=2)
    query_params = {
        "service" : 'frontend',
        #"operation" : args.operation,
        "start" : int(start_time.timestamp() * 1000000),
        "end" : int(end_time.timestamp() * 1000000),
        "limit" : 10000
    }
    args = {'file': '/dev/null', 'debug': True, 'query': query_params}
    
    res = preprocess_traces(
        pd.DataFrame(download(args)).set_index('traceID')
    )
    # TODO manage if want to save somewhere
    
else:       # read from existing file
    frontend = os.getenv('FRONTEND_SVC_NAME', 'frontend')
    dir = f"{basedir}/{timerange}/traces"
    resdir = f'{basedir}/{timerange}/results'
    res = preprocess_traces(
        load_traces(f'{dir}/{frontend}.csv.gz')
    )
    trace_stats = compute_trace_statistics(f'{dir}/{frontend}.csv.gz', dir)

#%% 
# bar plot of statistics
# filter dataframe keep only column named 'pippo'

sns.set_style('whitegrid')
data = pd.concat([x for x in trace_stats.values()], axis=1)
data = data.reset_index().melt(id_vars='operation', value_vars=trace_stats.keys())
data = data.query('operation != "/_healthz"')
sns.barplot(data, hue='operation', x='variable', y='value')
plt.ylabel('duration [ms]')
plt.xlabel('')
#plt.title('cartservice CPU limit: 2000m')
if saveplot:
    mysavefig(resdir + f'traces_statistics', bbox_inches='tight')
else:
    plt.show()


#%%
# plot for each operation the trace duration over time, 
# bin into 1second intervals, use max value

# filter to get anomalous traces
resampled = res #res.resample('1s').max().dropna()
resampled = resampled[resampled['operation'] != '/_healthz']
resampled['rpcErrors'] = resampled['rpcErrors'].astype(bool)

static_threshold = 500

if static_threshold is None:
    trace_sla_thresh = pd.read_csv(f'{dir}/traces_999th.csv', index_col='operation')
    resampled['faulty'] = resampled.apply(
            lambda x: (x['duration-ms'] > trace_sla_thresh.loc[x['operation']].iloc[0]) | x['rpcErrors'], 
            axis=1
        )
else:
    resampled['faulty'] = resampled.apply(
            lambda x: (x['duration-ms'] > static_threshold) | x['rpcErrors'], 
            axis=1
        )

# only plot faulty traces over time
for op in resampled['operation'].unique():
    sns.lineplot(data=resampled[(resampled['faulty']) & (resampled['operation'] == op)], 
                 x='startTime', 
                 y='duration-ms', 
                 marker='o',
                 label=op)
    plt.show()
#sns.lineplot(data=resampled, x='startTime', y='duration-ms')

#%% plot training set data distribution
sns.set_theme()
sns.displot(
    data=training, 
    x='duration-ms', 
    hue='operation', 
    multiple='stack',
    kind='hist',
    stat='probability',
    fill=True, 
    log_scale=True)
plt.title('Request duration distribution during training')
plt.show()