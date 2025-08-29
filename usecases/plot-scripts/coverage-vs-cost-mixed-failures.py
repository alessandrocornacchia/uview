
### This script was used to plot
# data for the NSDI 25 submission for death start bench workload with mixed failure type

#%%
import os, sys; 
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from utils import load_traces, mysavefig, preprocess_traces
from utils import compute_trace_statistics
import platform
import numpy as np
from globals import *

""" Reads file frontend_sketch_sampled.csv.gz which contains remaining traces after sampling
    the test dataset with PodSketch. Assume that sketch_tracer.py has been run before 
    this script."""


def extract_param_from_file_name(label, param):
        " Reads filename where parameters are separated by _ and returns values"
        l = label.split('_')
        for li in l:
            if li.startswith(param):
                return li.split(param)[1]
        return None


savefig = True
per_operation_thresh = '3-sigma' #, '95th'  # change to None to use static threshold of 200ms
alpha = 1 #1.2
frontend =  os.getenv('FRONTEND_SVC_NAME', 'frontend')
plotdir = None
plot_uview_vs_fixed_only = True
legend = False

#if 'DATASET_TIMEFRAME' not in globals():
experiments = {
    # 'all' : '14Sept0950',
    'all' : 'DSBHotel',
    # 'cpu' :         'VAE-SockShop-CPU',
    # 'memory' :      'VAE-SockShop-memory',
    # 'redis' :       'VAE-SockShop-redis',
}

# filter who to plot
PLOT_ONLY = ['head_5', 'head_20', 'best_config']

#else:
#    experiments = {
#        'generic' : 'DATASET_TIMEFRAME'
#    }

#%% Plot cost vs coverage scatterplot for all parameters

all_exp_df = []
for exp, DATASET_TIMEFRAME in experiments.items():
        
    print(f'Timeframe using {DATASET_TIMEFRAME}')
    
    frontend = "frontend" if "sockshop" in DATASET_TIMEFRAME.lower() else os.getenv('FRONTEND_SVC_NAME', 'frontend')

    resdir = f'{basedir}/{DATASET_TIMEFRAME}/results/'
    tracedir = f'{basedir}/{DATASET_TIMEFRAME}/traces'
    if plotdir is None:
        plotdir = resdir
        print(f"Saving plots in {plotdir}")

    res = pd.read_csv(f'{tracedir}/{frontend}_sketch_sampled.csv.gz', 
                        compression='gzip', 
                        parse_dates=['startTime', 'endTime'],
                        index_col='startTime')
    
    # oracle is if we hold sampling when we have introduced anomalies 
    res.rename(columns={'label': 'oracle'}, inplace=True)   
    res['oracle'] = res['oracle'].astype('bool')

    # remove /_healthz
    res = res[res['operation'] != '/_healthz']

    if per_operation_thresh is not None:
        
        # recompute trace statistics if not already computed, percentiles per operation
        if not os.path.exists(tracedir + f'traces_{per_operation_thresh}.csv'):
            print('Recomputing thresholds for anomalous traces')
            compute_trace_statistics(f'{tracedir}/{frontend}.csv.gz', tracedir)

        
        # use 3-sigma to classify ground truth traces TODO: why not user handler
        thresholds = pd.read_csv(os.path.join(tracedir, f'traces_{per_operation_thresh}.csv')).set_index('operation')
        
        
        # exclude from res operations for which we do not have thresholds
        operations_without_threshold = set(res['operation']) - set(thresholds.index)
        if len(operations_without_threshold) > 0:
            print("Operations not in training set:", operations_without_threshold, "skipping them.")
        res = res[res['operation'].isin(thresholds.index)]
        

        res['faulty'] = res.apply(
            lambda x: (x['duration-ms'] > alpha * thresholds.loc[x['operation']].iloc[0]) | x['rpcErrors'], 
            axis=1
        )
        
    else:
        th = 200
        res['faulty'] = (res['duration-ms'] > th) | res['rpcErrors']

    Nfaulty = res['faulty'].sum()
    Nerr = res['rpcErrors'].sum()


    cols = list(filter(
        lambda x: x.startswith('head') or x.startswith('k') or x == 'oracle' or x == "best_config", res.columns.values)
    )

    faultydf = res.where(res['faulty'])
    normaldf = res.where(res['faulty'] == False)
    # coverage (num faulty collected)
    coverage = faultydf[cols].sum()
    # overhead (num collected)
    overhead = res[cols].sum()
    #res[cols].sum()
    #overhead = res.query("faulty == False")[cols].sum()
    data = pd.DataFrame({'coverage': coverage, 'overhead': overhead}).reset_index()
    data['type'] = data['index'].apply(lambda x: x.split('_')[0])

    # normalize in absolute terms
    data['overhead_norm'] = 100 * data['overhead'] / len(res)
    data['coverage_norm'] = 100 * data['coverage'] / Nfaulty

    data['k'] = data['index'].apply(lambda x: extract_param_from_file_name(x, 'k'))
    data['l'] = data['index'].apply(lambda x: extract_param_from_file_name(x, 'l'))
    data['eta'] = data['index'].apply(lambda x: extract_param_from_file_name(x, 'eta'))
    data['t'] = data['index'].apply(lambda x: extract_param_from_file_name(x, 't'))
    data['legend'] = data['index'].apply(lambda x: '_'.join(x.split('_')[:-1]))
    #data['t'] = data['t']

    etas = data['eta'].dropna().unique()
    etas_num = np.array([float(e) / (10 ** (len(e)-1)) for e in etas])

    
    etas = np.array(['01', '001', '00'])
    etas_num = np.array([0.1, 0.01, 0])

    # idx = np.argsort(etas_num)
    # etas = etas[idx]
    # etas_num = etas_num[idx]
    # sizes = np.arange(len(etas), 0, -1) * 100
    eta_colors = sns.color_palette("viridis", len(etas))
    # reverse eta colors list
    eta_colors = eta_colors[::-1]

    if plot_uview_vs_fixed_only:
        fig = plt.figure(dpi=300, figsize=(2,1.5))

        for i in range(len(etas)):
            
            ax = sns.scatterplot(
                data=data[data['eta'] == etas[i]], 
                x='coverage_norm', 
                y='overhead_norm', 
                #hue='legend',
                #style='k',
                color=eta_colors[i],
                edgecolor='none',
                markers=True, 
                ax=plt.gca(),
                legend=i==0,
                #s=10,
                )

        # # plot the oracle
        # sns.scatterplot(
        #     data=data[data['index'] == 'oracle'],
        #     x='coverage_norm',
        #     y='overhead_norm',
        #     color='black',
        #     markers=True,
        #     # empty marker
        #     marker='o',
        #     edgecolor='black',
        #     facecolor='none',
        #     linewidth=1.5,
        #     ax=plt.gca(),
        #     s=40)

        # plot the optimal
        sns.scatterplot(
            data=data[data['index'] == 'best_config'],
            x='coverage_norm',
            y='overhead_norm',
            markers=True,
            # empty marker
            marker='o',
            edgecolor='none',
            #facecolor='none',
            color='red',
            linewidth=1.5,
            ax=plt.gca(),
            s=60)


        #plt.legend(bbox_to_anchor=(1.05, 1.05), loc=2, fontsize=8, ncol=1)
        if legend:
            plt.legend([f'$\\eta={e:g}$' for e in etas_num], loc='upper left', fontsize=8)

        #plt.ylabel('False Positive [%]')
        plt.ylabel(None)
        plt.xlabel('Coverage [%]')
        plt.grid(ls="-", alpha=0.4)
        plt.xlim([0,100])
        plt.ylim([0,100])

        # reduce axis line thickness
        # reduce thickness of the axis
        for axis in ['top','bottom','left','right']:
            ax.spines[axis].set_linewidth(0.5)

        # reduce thickness of the ticks
        ax.xaxis.set_tick_params(width=0.7)
        ax.yaxis.set_tick_params(width=0.7)
        
        ax.tick_params(axis='y', direction='in')
        ax.tick_params(axis='x', direction='in')

        if savefig:
            name = f'cost_vs_coverage_all_sketches-{exp}-uview_vs_fixed'
            if not per_operation_thresh:
                name = name + f'_fth{th}'
            mysavefig(plotdir + name, bbox_inches='tight', pad_inches=0)
        else:
            plt.show()

        #plt.title(f'# faulty={Nfaulty}, # error={Nerr}')
    else:
        fig = plt.figure(dpi=300, figsize=(5,4))

        for i in range(len(etas)):
            sns.scatterplot(
                data=data[data['eta'] == etas[i]], 
                x='coverage_norm', 
                y='overhead_norm', 
                hue='legend',
                style='k',
                palette='tab10',
                markers=True, 
                ax=plt.gca(),
                legend=i==0,
                s=sizes[i])

        # plot the oracle
        sns.scatterplot(
            data=data[data['index'] == 'oracle'],
            x='coverage_norm',
            y='overhead_norm',
            color='black',
            markers=True,
            # empty marker
            marker='o',
            edgecolor='black',
            facecolor='none',
            linewidth=1.5,
            ax=plt.gca(),
            s=100)

        # plot the optimal
        sns.scatterplot(
            data=data[data['index'] == 'best_config'],
            x='coverage_norm',
            y='overhead_norm',
            color='black',
            markers=True,
            # empty marker
            marker='o',
            edgecolor='red',
            facecolor='none',
            linewidth=1.5,
            ax=plt.gca(),
            s=100)


        plt.legend(bbox_to_anchor=(1.05, 1.05), loc=2, fontsize=8, ncol=1)
        #plt.legend(loc='lower right', fontsize=8)

        plt.ylabel('Overhead [False Positive %]')
        plt.xlabel('Coverage [%]')
        plt.grid()
        plt.xlim([0,100])
        plt.ylim([0,100])
        plt.title(f'# faulty={Nfaulty}, # error={Nerr}')

        if savefig:
            name = f'cost_vs_coverage_all_sketches-{exp}'
            if not per_operation_thresh:
                name = name + f'_fth{th}'
            mysavefig(plotdir + name, bbox_inches='tight')
        else:
            plt.show()

    # here we filter only the algorithms we want to plot, for all experiments
    idx = PLOT_ONLY
    dff = []
    for i in idx:
        dff.append(data.query(f'index == "{i}"'))
    all_exp_df.append(pd.concat(dff))
    all_exp_df[-1]['experiment'] = exp

#%%

########################################################################## INDEPENDENT ON ABOVE !!! RUN INTERACTIVELY ##########################################################################
# plot scatter plot of coverage vs overhead: 
#  - coverage vs overhead for different failure types on the same graph
#  - compares head sampling strategies with sketch sampling strategy, where sketch uses optimal fine tuned parameters
#  

savefig = False

res = pd.concat(all_exp_df)

pal = sns.color_palette("muted")
#res.legend = 2* ['head-1%', 'head-20%', 'w/microview']
res['legend'] = res[['index', 'experiment']].apply(lambda x: x['index'].replace('_', '-') + ', ' + x['experiment'], axis=1)

# plt.figure(dpi=300, figsize=(4,3))
# # plot the optimal
# sns.scatterplot(
#     data=res,
#     x='coverage_norm',
#     y='overhead_norm',
#     hue='experiment',
#     markers=True,
#     style='index',
#     # empty marker
#     ax=plt.gca(),
#     s=200)
# plt.grid()
# plt.xlim([0,100])
# plt.ylim([0,100])
# plt.xlabel('Coverage [%]')
# plt.ylabel('Overhead [%]')
# plt.legend(ncol=2, fontsize=6)
# plt.show()

# plot histograms (like in uView workshop paper)

fig, ax = plt.subplots(1,2, dpi=1200, figsize=(5,2))

res['algorithm'] = res['index'].apply(lambda x: x.replace('_', '-'))
res['algorithm'] = res['algorithm'].apply(lambda x: x if x != 'best-config' else '$\mu$View')

sns.barplot(res, 
            x='experiment', 
            y='coverage_norm', 
            hue='algorithm', 
            ax=ax[0],
            palette=pal,
            edgecolor='black',
            width=0.5)
ax[0].legend([], [], frameon=False)
ax[0].set_ylim([0,100])
ax[0].grid(linestyle=':', c='black', alpha=0.4)
ax[0].set_xlabel('')
ax[0].set_ylabel('Coverage [%]')
# put legend on top
plt.figlegend(bbox_to_anchor=(0.05, 1.12), loc=2, ncol=4)
#plt.show()
#mysavefig('./coverage', bbox_inches='tight')

#plt.figure(dpi=300, figsize=(4,2.5))
sns.barplot(res, x='experiment', 
            y='overhead_norm', hue='algorithm', ax=ax[1],
            edgecolor='black', palette=pal, width=0.5)

ax[1].set_ylim([0,100])
ax[1].legend([], [], frameon=False)
ax[1].set_xlabel('')
ax[1].set_ylabel('Overhead [%]')
ax[1].grid(linestyle=':', c='black', alpha=0.4)
#plt.legend(bbox_to_anchor=(-0.05, 1.15), loc=2, fontsize=7, ncol=4)
fig.tight_layout()
if savefig:
    mysavefig(plotdir + 'coverage-overhead', bbox_inches='tight')
plt.show()

# dump to csv
columns = ['experiment', 'algorithm', 'coverage_norm', 'overhead_norm', 'coverage', 'overhead']
res.to_csv(plotdir + 'coverage-overhead.csv', index=False)

#%% Plot intersections vs operation

plt.figure(figsize=(6,3))
res.groupby(by='operation')[['faulty', 'best_config', 'oracle']].sum().plot.bar(ax=plt.gca(),rot=10)
plt.ylabel('# collected')
if savefig:
    name = f'collected-traces-by-op'
    if not per_operation_thresh:
        name = name + f'_fth{th}'
    mysavefig(resdir + name, bbox_inches='tight')
else:
    plt.show()

Normalizer = faultydf[['traceID', 'operation']].dropna().groupby(by='operation').count()
oracle_and_faulty = res.query('(faulty == True) & (oracle == True)').groupby(by='operation')[['traceID']].count().rename(columns={'traceID': 'oracle & gt'})
optimal_and_faulty = res.query('(faulty == True) & (best_config == True)').groupby(by='operation')[['traceID']].count().rename(columns={'traceID': 'sketch & gt'})
oracle_and_optimal = res.query('(oracle == True) & (best_config == True)').groupby(by='operation')[['traceID']].count().rename(columns={'traceID': 'sketch & oracle'})# / res['best_config'].sum()

# normalization
oracle_and_faulty = oracle_and_faulty.div(Normalizer.traceID, axis=0)
optimal_and_faulty = optimal_and_faulty.div(Normalizer.traceID, axis=0)
Normalizer = res.where(res['oracle'])[['traceID', 'operation']]\
                .dropna()\
                .groupby(by='operation')\
                .count()
oracle_and_optimal = oracle_and_optimal.div(Normalizer.traceID, axis=0)

joined = oracle_and_faulty.join(optimal_and_faulty, how='left')\
                 .join(oracle_and_optimal, how='left')
plt.figure(figsize=(6,3))
joined.plot.bar(rot=10,ax=plt.gca())
plt.title('Intersection of collected trace sets')
plt.legend(ncols=3)
plt.ylim(0,1.2)
plt.ylabel('| intersection | / | 2nd set |')
if savefig:
    name = f'intersections-by-op'
    if not per_operation_thresh:
        name = name + f'_fth{th}'
    mysavefig(resdir + name, bbox_inches='tight')
else:
    plt.show()

