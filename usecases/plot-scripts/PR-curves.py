#%% 
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import seaborn as sns
from utils import mysavefig
from globals import services, net_experiment

"""
Plots in the same graph precision-recall curves for all configurations of a given service.
"""

timerange = net_experiment
theshold_p = 99.9
resdir = 'results_wth'
# plot all PR curves on same graph
for service in services:

    directory = f'./{resdir}/{timerange}/{service}/'
    subdirs = os.listdir(directory)
    # keep only those with threshold in name
    subdirs = [s for s in subdirs if f't{theshold_p:.1f}' in s]

    # enter each subdir and join in a pandas dataframe all the precision_recall.csv files
    df = pd.DataFrame()
    for subdir in subdirs:
        subdir = directory + subdir
        if os.path.isdir(subdir):
            df_temp = pd.read_csv(subdir + '/precision_recall.csv')
            df_temp['config'] = subdir.split('/')[-1]
            df = pd.concat([df, df_temp], ignore_index=True)

    # plot all PR curves on same graph
    fig, ax = plt.subplots()
    sns.lineplot(data=df, x='recall', y='precision', hue='config', ax=ax)
    ax.set_title(f'Precision-Recall curves for {service} service')
    ax.set_xlabel('Recall')
    ax.set_ylabel('Precision')
    plt.grid()
    mysavefig(f'./{resdir}/{timerange}/precision_recall', bbox_inches='tight')
    #plt.show()