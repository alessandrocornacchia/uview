#%% 
import os, sys; 
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from utils import mysavefig
import platform
import numpy as np
from globals import *
import copy

savefig = True
resdir = f'{basedir}/{DATASET_TIMEFRAME}/results/'
anomalies = f'{basedir}/{DATASET_TIMEFRAME}/faults.csv'

#%% # join all classification results in a single dataframe

faulty_services = pd.read_csv(anomalies, usecols=['service']).service.unique()
services = [d for d in os.listdir(resdir) if os.path.isdir(os.path.join(resdir, d))]

# sanity check, assert we have same names in faulty services (taken from anomaly file) and the ones we derive from the results
num_name_conflicts = list(set(services) - set(faulty_services))
if len(num_name_conflicts):
    for i in range(len(faulty_services)):
        for j in range(len(services)):
            if services[j] in faulty_services[i]:
                print(f"{faulty_services[i]} resolved to {services[j]}")
                faulty_services[i] = services[j]
                break

try:
    assert len(set(services) - set(faulty_services)) == 0
except AssertionError:
    print(f"Name conflicts: {num_name_conflicts}")
    print(f"Faulty services: {faulty_services}")
    print(f"Services: {services}")
    sys.exit(1)

dfs = []
for svc in services:
    for x in os.listdir(f'{resdir}/{svc}'):
        file  = f'{resdir}/{svc}/{x}/results.csv'
        if os.path.exists(file):
            dfs.append(pd.read_csv(file))
res = pd.concat(dfs)

#%% Find best configuration for each service

# for faulty services we look for high F1
print('Computing best configuration for faulty:', faulty_services)
quoted_faulty_services = ['"' + x + '"' for x in faulty_services]
best_faulty = res.query(f'service in [{", ".join(quoted_faulty_services)}]')\
   .sort_values(by=['service','f1'], ascending=False)\
   .groupby(by='service')\
   .head(1)



# for non-faulty services we look for low FPR
non_faulty = list(set(services) - set(faulty_services))

print('Computing best configuration for non-faulty:', non_faulty)
quoted_non_faulty = ['"' + x + '"' for x in non_faulty]
best_non_faulty = res.query(f'service in [{", ".join(quoted_non_faulty)}]')\
   .sort_values(by=['service','fpr'])\
   .groupby(by='service')\
   .head(1)

best_config = pd.concat([best_faulty, best_non_faulty])
best_config.to_csv(resdir+'best_config_parameters_and_performance.csv', index=False)

# also plot it
plt.figure(figsize=(5,2))
# best_faulty['x'] = best_faulty['service'].apply(lambda x: x.split('service')[0])
# best_config['x'] = best_config['service'].apply(lambda x: x.split('service')[0])
best_config[['service', 'f1', 'fpr']].sort_values(by='f1', ascending=False)\
                               .plot.bar(x='service', rot=80, ax=plt.gca())
plt.xlabel('')
plt.title('Optimal configuration for each service')
plt.grid(axis='y', alpha=.8)

for xtick in plt.gca().get_xticklabels():
    if xtick.get_text() in best_faulty.service.values:
        xtick.set_color('red')
if savefig:
    mysavefig(f'{resdir}/best-config-f1-fpr-vs-svc', bbox_inches='tight')
else:
    plt.show()

#%%
# for faulty services plot precision, recall and f1
common_bests = None
for svc in faulty_services:
    data=res.query(f'service == "{svc}"').sort_values(by='recall')
    data['configuration'] = 'k' + data["k"].astype(str) + '_l' + data["l"].astype(str) + '_th' + data["threshold"].astype(str) + '_eta' + data["eta"].astype(str)

    plt.figure(figsize=(5,2))
    data[['configuration', 'precision', 'recall']].tail(10)\
        .plot\
        .bar(x='configuration', ax=plt.gca(), rot=80)
    #data = data.melt(id_vars=['configuration'], value_vars=['precision', 'recall'])
    plt.title(svc)
    plt.legend(loc='lower center', ncol=2)
    if savefig:
        mysavefig(f'{resdir}/{svc}/precision-recall', bbox_inches='tight')
    else:
        plt.show()

    # F1 score
    top10 = data[['configuration', 'f1']].sort_values('f1').tail(20)

    if common_bests is None:
        common_bests = top10[['configuration']]
    else:
        common_bests = pd.merge(common_bests, top10[['configuration']], on='configuration')
    print("Common top-10 (F1 score) sketch configurations (only useful for faulty services): ")
    print(common_bests)

    plt.figure(figsize=(5,2))
    top10.plot\
    .bar(x='configuration', ax=plt.gca(), rot=80)
    #data = data.melt(id_vars=['configuration'], value_vars=['precision', 'recall'])
    plt.title(svc)
    if savefig:
        mysavefig(f'{resdir}/{svc}/f1', bbox_inches='tight')
    else:
        plt.show()

#%%
for svc in non_faulty:
    data=res.query(f'service == "{svc}"').sort_values(by='fpr', ascending=False)
    data['configuration'] = 'k' + data["k"].astype(str) + '_l' + data["l"].astype(str) + '_th' + data["threshold"].astype(str) + '_eta' + data["eta"].astype(str)

    top = data[['configuration', 'fpr', 'accuracy']].tail(20)
    common_bests = pd.merge(common_bests, top[['configuration']], on='configuration')
    print(common_bests)
    plt.figure(figsize=(5,2))
    top.plot\
        .bar(x='configuration', ax=plt.gca(), rot=80)
    #data = data.melt(id_vars=['configuration'], value_vars=['precision', 'recall'])
    plt.title(svc)
    if savefig:
        mysavefig(f'{resdir}/{svc}/fpr-accuracy', bbox_inches='tight')
    else:
        plt.show()
# %%
