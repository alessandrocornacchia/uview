#%%
import os, sys; 
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import platform
import numpy as np
import glob


def mysavefig(f, verbose=True, **kwargs):
    if verbose:
        print(f'Saving to {f}')
    directory = os.path.dirname(f)

    plt.savefig(directory + f+'.png', **kwargs)
    plt.savefig(directory + f+'.pdf', **kwargs)
    plt.close()


savefig = True
k = 10
l = 25
resdir = f'./artifacts/results/redis-cart/'

"""
Bar plot with precision and recall for each configuration
"""
#%%
# join all classification results
# use glob matching to match all file of kind threshold_*.csv

print(f'Loading results from {resdir}')
files = glob.glob(
    './**/ratios-*.csv', 
    root_dir='./', 
    recursive=True
    )

dfs = []
for f in files:
    print(f)
    dfs.append(pd.read_csv(f, index_col=0))

df = pd.concat(dfs, ignore_index=True)

#%%
sns.set(rc={'figure.figsize':(5,3)})
sns.set_style(style="whitegrid")
sns.set_context(context="paper", font_scale=1.25)

PROPS = {
    'boxprops':{'facecolor':'aliceblue', 'edgecolor':'black'},
    'medianprops':{'color':'blue', 'linewidth':2},
    'whiskerprops':{'color':'black'},
    'capprops':{'color':'black'}
}

df['x'] = df['threshold'].apply(lambda x: np.round(x/100, 3))
ax = sns.boxplot(data=df, 
                 y='correlations', 
                 x='x', 
                 width=0.3,

                 **PROPS)
#ax2 = plt.twinx()
#x = df['threshold'].unique()
#y = df.groupby('threshold').first()['Storage']
plt.xlabel('Anomaly Score Threshold ($\gamma$)')
plt.ylabel('Normalized Correlation (Avg)')
mysavefig('corrrelation-vs-sampling-aggressiveness', bbox_inches='tight')

#%%
total_samples = 841
df['Storage'] = (total_samples - df['num_samples'])/total_samples * 100
res = df.groupby("x").first()['Storage']
# reindex to have x as column
res = res.reset_index()
res['x'] = res['x'].apply(lambda x: f'{x:g}')


sns.set(rc={'figure.figsize':(5,1.1)})
sns.set_style(style="whitegrid")
sns.set_context(context="paper", font_scale=1.25)

res.plot(x='x', y='Storage', marker="|", lw=1.75, markersize=8)
#sns.lineplot(df, y='Storage', x='threshold', color='darkred', markers=True)
plt.ylabel('Data volume\n reduction [%]')
plt.xlabel('Anomaly Score Threshold ($\gamma$)')
# remove legend
plt.legend('', frameon=False)
# specify x ticks
plt.xticks(res.index.values, fontsize=12)
plt.ylim([0,100])
#plt.show()
mysavefig('storage-vs-sampling-aggressiveness', bbox_inches='tight')

