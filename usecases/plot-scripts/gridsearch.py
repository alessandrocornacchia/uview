#%% 
import itertools
import os, sys; 
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from utils import mysavefig
from globals import *

"""
Read csv file containing all performance metrics in the order (k,l,th,f1,precision,recall,fpr),
Gives set of Grid plots with k on the x axis, l on the y axis and the other metrics as heatmaps.
The threshold th should go in the title of each plot, along with the metric name. """

DATASET_TIMEFRAME = '202307261137-202307261237'
directory = f'{basedir}/{DATASET_TIMEFRAME}/results'

#%% Aggregate plot (i.e., performance of classifier obtained by merging sketches)
plt.style.use('default')

df = pd.read_csv(directory + 'performance.csv')
ths = [99, 99.9]
etas=[0, 0.1, 0.01]

metrics = ['f1','precision','recall','fpr']
saveplot = False

#%%
for m in metrics:
    for th in ths:
        for eta in etas:
            data = df[(df['th'] == th) & (df['eta'] == eta)]
            # if dataframe not empty (it might happen if we provide configurations that do not exist)
            if not data.empty:
                data = data.pivot(index='l', columns='k', values=m)
                fig, ax = plt.subplots(figsize=(6,4), dpi=300)
                sns.heatmap(data, annot=True, fmt='.3f', cmap='Blues', ax=ax)
                ax.set_title(f'{m}, th={th}th percentile, eta={eta}')
                if saveplot:
                    mysavefig(f'{directory}/grid_{m}_th{th}_eta{eta}', bbox_inches='tight')
                else:
                    plt.show()

#%% individual classifiers
""" Go into directories and read performance metrics such as f1, precision, recall,
aggregate into a single dataframe for all services. """

service_dirs = [x for x in os.listdir(directory) if os.path.isdir(directory + x)]
ks = [10,15,20]
ls = [25, 50]
dfs = []

for svc in service_dirs:
    print(f'Plotting sensitivity analysis for service {svc}')
    for k,l,th,eta in itertools.product(ks,ls,ths,etas):

        configlabel = f'k{k}_l{l}_t{th:.1f}_eta{float(eta)}'
        print('[OK]' + configlabel)
        file = f'{directory}{svc}/{configlabel}/results.csv'
        if os.path.exists(file):            
            df = pd.read_csv(file)
            df['service'] = svc
            dfs.append(df)

data = pd.concat(dfs)
#%% plot analysis
metrics = [('precision', 'Blues'), ('recall', 'YlOrBr')]
for svc in service_dirs:
    for metric, cmap in metrics:
        for eta,th in itertools.product(etas,ths):
            res = data.query(f'service == "{svc}"').query(f'threshold == {th:.1f}').query(f'eta == {float(eta)}')
            res = res.pivot(index='l', columns='k', values=metric)
            fig, ax = plt.subplots(figsize=(4,3), dpi=300)
            sns.heatmap(res, annot=True, fmt='.3f', cmap=cmap, ax=ax)
            #ax.set_title(f'{metric}, th=99th percentile, eta=0.1, {svc}')
            mysavefig(f'{directory}{svc}/grid_{metric}_th_{th:.1f}_eta_{eta}', bbox_inches='tight')
#res = data.query('service == "recommendationservice"').query('threshold == 99.0').query('eta == 0.1')
#res = res.pivot(index='l', columns='k', values='precision')
#sns.heatmap(res, annot=True, fmt='.3f', cmap='Blues')