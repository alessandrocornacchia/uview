#%%
import os, sys; 
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import platform
import pandas as pd
import matplotlib.pyplot as plt
from utils import mysavefig, label_anomalous_samples
from globals import *

#timerange = '202307042041-202307042151'
#timerange = '202308020913-202308021013' #cpu
timerange = '202312041030-202312041100' # redis
anomalies_path = f"{basedir}/{timerange}/faults.csv"
# aggregate score vs time
k=15
l=50
th=99.0
eta=0
saveplot = False
directory = f'{basedir}/{timerange}/results'

configlabel = f'k{k}_l{l}_t{th:.1f}_eta{float(eta)}'
configlabel = 'best_config'
#configlabel = f'k{k}_l{l}_t{th:.1f}'

df = pd.read_csv(
    directory + f'{configlabel}.csv', 
    parse_dates=['timestamp']
).set_index('timestamp')

# only interested in list of tuples for anomalies
_, anomalies = label_anomalous_samples(pd.DataFrame(), anomalies_path)
AID = 2

# plot scores over time
ax = df[df['predicted'] == True].plot.line(
    y='score', 
    style='*', 
    color='r',
    label='Anomalous')
df.plot.line(
    y='score', 
    ax=ax,
    label='Not anomalous')
for a in anomalies:
    plt.axvspan(a[0], a[1], facecolor='r', alpha=0.2)
plt.legend()
plt.ylabel('Anomaly Score')
plt.xlim([df.index[0], df.index[-1]])
plt.title(configlabel)
if saveplot:
    mysavefig(f'{directory}/scores_{configlabel}', bbox_inches='tight')
else:
    plt.show()