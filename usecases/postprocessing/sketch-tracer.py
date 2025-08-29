#%%
import pandas as pd
import random
import matplotlib.pyplot as plt
from utils import load_traces, mysavefig
import platform
import os
import sys
from utils import label_anomalous_samples
from globals import *

"""
    Reads outcome of sketch classifications and samples traces accordingly.
    It produces a CSV files where we have different columns for different sketch 
    parameters, and binary values indicating if trace is collected or not.
"""

def sketch_sample(LUT, x):
    """
    returns true if last sample processed by PodSketch is classified anomalous
    """
    return LUT.truncate(after=x).tail(1).reset_index().loc[0,'predicted']


savefig = True

resdir = f'{basedir}/{DATASET_TIMEFRAME}/results'
include_head = False

print(f"Running tracing tool, detection algorithm: {os.environ.get('ALGORITHM').lower()}")
# all available classifications for different sketch parameters (only if FDsketch is used)

if os.environ.get("ALGORITHM").lower() == "fdsketch":
    sketch_classifications = [csv for csv in os.listdir(resdir) if csv.endswith('.csv') and csv.startswith('k')]
else:
    sketch_classifications = []

# in any case there is the best configuration
sketch_classifications.append('best_config.csv')

#
# Read traces and sample them according to the LUT: i.e., if previous sample in LUT is anomalous, 
# then sample trace, otherwise resort to head based sampling
# Automatically detect frontend trace file
traces_dir = f'{basedir}/{DATASET_TIMEFRAME}/traces'
frontend_files = [f for f in os.listdir(traces_dir) if 'frontend' in f.lower() and f.endswith('.csv.gz')]

# Get the main frontend file (excluding sampling files)
frontend_files = [f for f in frontend_files if 'sampl' not in f]

if frontend_files:
    frontend_file = frontend_files[0]  # Use the first matching file
    # Extract service name without extension for later use
    frontend = frontend_file.split('.')[0]
    print(f"Detected frontend service file: {frontend_file}")
else:
    # Fallback to environment variable
    frontend = os.getenv('FRONTEND_SVC_NAME', 'frontend')
    print(f"No frontend trace file detected, using default: {frontend}")



FILE = f'{basedir}/{DATASET_TIMEFRAME}/traces/{frontend}.csv.gz'
anomalies_path = f"{basedir}/{DATASET_TIMEFRAME}/faults.csv"

print(f'==> Reading traces from {FILE}')

traces = load_traces(FILE)

traces['startTime'] = pd.to_datetime(traces['startTime'], unit='us', utc=True).dt.tz_convert('Asia/Riyadh')
traces['endTime'] = pd.to_datetime(traces['endTime'], unit='us', utc=True).dt.tz_convert('Asia/Riyadh')
traces = traces.sort_values(by='startTime').set_index('startTime')
# creates a column 'label' which tells if trace has been collected during injectd anomaly
traces, anomalies = label_anomalous_samples(traces, anomalies_path)

print(traces.head())
#%%
flag = True
for skc in sketch_classifications:        
    # read classification of this sketch
    print(skc)

    LUT = pd.read_csv(
        os.path.join(resdir, skc), 
        parse_dates=['timestamp'], 
        usecols=['timestamp', 'predicted'],
        index_col='timestamp'
    )

    if flag:
        flag = False
        LUT_s = LUT.index[0]
        LUT_e = LUT.index[-1]
        # keep only traces that have been collected during the same time interval of the LUT
        traces = traces[LUT_s:LUT_e]

    col = ''.join(skc.split('.')[:-1])
    traces[col] = traces.apply(lambda x: sketch_sample(LUT, x.name), axis=1)

# here:

#  we add all traces sampled for different head sampling percentages and we as well compute
# the union of sketch and head sampling
percentage = [1, 5, 10, 20]
for p in percentage:
    try:
        print(f'==> Reading head sampled traces with percentage {p:.1f}x')
        # read head sampled traces with percentage p
        headdf = load_traces(
            f'{basedir}/{DATASET_TIMEFRAME}/traces/{frontend}_sampling_{p:.1f}x.csv.gz', 
        )
    except FileNotFoundError:
        print(f'File not found: {basedir}/{DATASET_TIMEFRAME}/traces/{frontend}_sampling_{p:.1f}x.csv.gz. Skipping...')
        continue

    headdf['startTime'] = pd.to_datetime(headdf['startTime'], unit='us', utc=True).dt.tz_convert('Asia/Riyadh')
    headdf.set_index('startTime', inplace=True)
    headdf[f'head_{p}'] = 1
    # sort values by index, keep only those in LUT interval
    headdf = headdf.sort_values(by='startTime')[LUT_s:LUT_e]

    # join head sampled traces with sketch sampled traces
    # we use outer join to keep all traces in sketch, and then fill NaN with
    # zeros to account for those not present in head sampling file
    traces = headdf[[f'head_{p}']].join(
        traces, 
        how='outer').fillna(0)
    # convert index to tz Asia/Riyadh
    traces.index = traces.index.tz_convert('Asia/Riyadh')
    #traces[f'sketch+head_{p}'] = traces.apply(lambda x: max(x[f'head_{p}'], x['sketch']), axis=1)

traces.to_csv(
    f'{basedir}/{DATASET_TIMEFRAME}/traces/{frontend}_sketch_sampled.csv.gz',
    compression='gzip'
)