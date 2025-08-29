#%%
import os
import pandas as pd
import matplotlib.pyplot as plt
from utils import label_anomalous_samples, mysavefig
import sklearn
import platform
import itertools
import sys
from globals import *


def aggregate_classifications(files):
    """
    Given the output of all sketches, aggregates their results
    If at least one sketch detects an anomaly, the sample is labeled as anomalous
    """

    # TODO here: aggregate only a subset of sketch output, then use this
    # caveat: you should call this function when you trace, why doing it before?
    
    for i in range(len(files)):
        try:
            df = pd.read_csv(files[i], parse_dates=['timestamp']).set_index('timestamp')
            service_name = files[i].split('/')[-3]
            
            if 'predicted' in df.columns:
                df.rename(columns={'predicted': f'predicted_{service_name}'}, inplace=True)
            if 'score' in df.columns:
                df.rename(columns={'score': f'score_{service_name}'}, inplace=True)
            if 'label' in df.columns:
                df.rename(columns={'label': f'label_{service_name}'}, inplace=True)
            
            print('[OK]' + configlabel + f'. Used {len(files)} sketches/services in the classification')
            break
        except FileNotFoundError:
            pass
    
    # no valid configuration found, there is nothing to aggregate
    if i+1 == len(files):
        return None
    
    # merge with all other configurations
    for classification_pod_i in files[i+1:]:
        service_name = classification_pod_i.split('/')[-3]
        try:
            df_temp = pd.read_csv(
                classification_pod_i, parse_dates=['timestamp']
            ).set_index('timestamp')
            if 'predicted' in df_temp.columns:
                df_temp.rename(columns={'predicted': f'predicted_{service_name}'}, inplace=True)
            if 'score' in df_temp.columns:
                df_temp.rename(columns={'score': f'score_{service_name}'}, inplace=True)
            if 'label' in df_temp.columns:
                df_temp.rename(columns={'label': f'label_{service_name}'}, inplace=True)
            df = df.join(df_temp)
        except FileNotFoundError:
            print(f'Not using {classification_pod_i}')
            continue        

    # Merge sketches (OR between labels: anomaly if at least one micros is anomalous)
    df['label'] = df[[c for c in df.columns if 'label' in c]].max(axis=1)
    df['predicted'] = df[[c for c in df.columns if 'predicted' in c]].max(axis=1)
    df['score'] = df[[c for c in df.columns if 'score' in c]].max(axis=1)
    return df




#%%

# TODO these parameters must not go here (better to read from outside)
anomalies_path = f"{basedir}/{DATASET_TIMEFRAME}/faults.csv"
ks = [10, 15, 20, 30] 
ls = [25, 50]
ths = [99, 99.9]
etas = [0, 0.01, 0.1]

saveplot = True
directory = f'{basedir}/{DATASET_TIMEFRAME}/results/'
service_dirs = [x for x in os.listdir(directory) if os.path.isdir(os.path.join(directory, x))]

header = ['k','l','th','eta','f1','precision','recall','fpr']
#service_dirs.remove('frontend') # TODO remove if you also want to use frontend !!

#%% Assume all sketches would have the same configuration of the hyper-parameters, plot the performance of each sketch
with open(directory + 'performance.csv', 'w') as f:
        f.write(','.join(header) + '\n')

for k,l,th,eta in itertools.product(ks,ls,ths,etas):
    
    configlabel = f'k{k}_l{l}_t{th:.1f}_eta{float(eta)}'
    files = [f'{directory}{svc}/{configlabel}/classification.csv' for svc in service_dirs]
    df = aggregate_classifications(files)
    if df is not None:  # for non valid combinations of parameters it might return none
        
        df.to_csv(directory + f'{configlabel}.csv')
        
        f1 = sklearn.metrics.f1_score(df.label.values, df.predicted.values)
        precision = sklearn.metrics.precision_score(df.label.values, df.predicted.values)
        recall = sklearn.metrics.recall_score(df.label.values, df.predicted.values)

        tn, fp, fn, tp = sklearn.metrics.confusion_matrix(
            df.label.values, 
            df.predicted.values).ravel()

        fpr = fp / (fp + tn)

        # append to csv all performance metrics
        with open(directory + 'performance.csv', 'a') as f:
            f.write(f'{k},{l},{th:.1f},{eta},{f1},{precision},{recall},{fpr}\n')

#%% Aggregate sketches using best configuration for each service
best_config = pd.read_csv(directory + 'best_config_parameters_and_performance.csv')
configs = best_config.apply(
    lambda x: f'{x["service"]}/k{x["k"]}_l{x["l"]}_t{x["threshold"]:.1f}_eta{float(x["eta"])}', 
    axis=1
)
files = [f'{directory}{c}/classification.csv' for c in configs]
df = aggregate_classifications(files)
df.to_csv(directory + f'best_config.csv')