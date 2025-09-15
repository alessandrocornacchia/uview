#%%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from timeit import default_timer as timer
from classifiers import AnomalyClassifier
from utils import plot_score_distribution, plot_precision_recall
from utils import label_anomalous_samples
from utils import col_name_to_metric
from utils import mysavefig
from fdsketch.frequentDirections import FastFrequentDirections, FrequentDirections
from sklearn.metrics import f1_score, precision_score, confusion_matrix, recall_score, accuracy_score
import argparse
import sys

############ default args (overriden by cmd line)
SERVICE = 'redis-cart'
DATASET_TIMEFRAME = '202312041030-202312041100'
l = 25
k = 10
threshold_p = 50
eta = 0
save_to_disk = f'/data/scratch/cornaca/results'
workdir = "/data/scratch/cornaca/datasets/metrics"
debug=False
available_tasks = ['classify', 'plot_metrics', 'dynamic_sampling', 'plot_metrics_hpa']
task = 'classify'
ids = [12]
############

#%% DO NOT EXECUTE IN INTERACTIVE MODE
if __name__ == "__main__":
    
    args = argparse.ArgumentParser()
    args.add_argument("--service", "-s", type=str, help="Service name", required=True)
    args.add_argument("--time", "-t", type=str, help="Timeframe", required=False)
    args.add_argument("-k", type=int, help="Sketch size", required=True)
    args.add_argument("-l", type=int, help="Number of components", required=True)
    args.add_argument("--threshold", "-th", type=float, help="Threshold for anomaly detection (as percentile)", default=99)
    args.add_argument("--dir", "-d", type=str, help="Working directory", default=".")
    args.add_argument("--learning-rate", type=float, default=0.1, help="Learning rate for sketch update")
    args.add_argument("--debug", action='store_true', help="Debug mode")
    args.add_argument("--task", type=str, default="classify", help=f"Available tasks: {available_tasks}")
    args.add_argument("--ids", type=int, nargs='+', help=f"IDs of metrics to plot, space separated. Valid only if task is plot_metrics")

    args = args.parse_args()

    SERVICE = args.service
    DATASET_TIMEFRAME = args.time
    l = args.l
    k = args.k
    threshold_p = args.threshold
    basedir = args.dir
    workdir = os.path.join(args.dir, 'metrics')
    save_to_disk = os.path.join(args.dir, 'results')
    eta = args.learning_rate
    debug = args.debug
    task = args.task
    ids = args.ids

#%%
if save_to_disk is not None:
    directory = f'{save_to_disk}/{SERVICE}/k{k}_l{l}_t{threshold_p}_eta{eta}'
    print('Writing results to: ', directory, '...')
    if not os.path.exists(directory):
        os.makedirs(directory)
    logf = open(f'{directory}/log.txt', 'w')
else:
    logf = sys.stdout

#%%---------------------------- experiments ----------------------------

# parameters
TRAIN_FILE = f'{workdir}/{SERVICE}/data_train.csv'
TEST_FILE = f"{workdir}/{SERVICE}/data_test.csv"
COL_DESC_FILE = os.path.dirname(TRAIN_FILE) + '/column_desc_test.json'
anomalies_path = f"{basedir}/faults.csv"
drop = False
normalize = True
nc = 50

df_train = pd.read_csv(TRAIN_FILE, index_col='timestamp', parse_dates=['timestamp'])
df_test = pd.read_csv(TEST_FILE, index_col='timestamp', parse_dates=['timestamp'])

#df_train = df_train.replace(0, method='ffill')
#df_test = df_test.replace(0, method='ffill')

if drop:
    cols = ['value_74', 'value_36', 'value_35'] # container_last_seen, container_start_time
    #cols = df_train.columns.values[-nc:]
    #col_to_drop = random.sample(list(df_train.columns.values[37:]), nd) # 
    df_train = df_train.drop(pd.Series(cols, dtype=object).unique(), axis=1)
    df_test = df_test.drop(pd.Series(cols, dtype=object).unique(), axis = 1)
    with open(f'dropped_{nc}.txt', 'w') as f:
        for e in col_name_to_metric(cols, COL_DESC_FILE): 
            print(e, file=f)

if normalize:
    mu = df_train.mean()
    std = df_train.std()
    df_train = ((df_train - mu)/ std).fillna(0)
    # we compute mean and std over training data. It might happen that a metric
    # is all zero, then in the test data it has some samples. In this case 
    # we don't have an estimate of the standard deviation (it is actually an outlier)
    # therefore we replace it with 1 i.e.,  we don't normalize it
    std.replace([0], 1, inplace=True)
    df_test = ((df_test - mu)/ std).fillna(0)


#Anomalous intervals
df_test, anomalies = label_anomalous_samples(df_test, anomalies_path, SERVICE)
num_anomalous_metric_samples = len(df_test[df_test['label'] == 1])
print("Number of anomalies labeled:", num_anomalous_metric_samples)

# write to disk the labeled test file
labeled_file = TEST_FILE.replace('.csv', '_labeled.csv')
try:
    df_test.to_csv(labeled_file)
except:
    print("Error writing to disk labeled file, please check the path")
    raise

print("Labeled test file written to disk:", labeled_file)

# uncomment to label only gt without classification steps
# sys.exit(0)

if num_anomalous_metric_samples == 0:
    if task != "dynamic_sampling":
        print("No anomalies found in the test set, exiting...")
        sys.exit(0)

# classifier parameters
n = len(df_train)                 # stream size
m = len(df_train.columns)         # number of features
        
if k > l:
    raise argparse.ArgumentTypeError("k must be smaller than l")
if l > m:
    raise argparse.ArgumentTypeError("l must be smaller than m")

#%%
   
# sketch based classifier
classifier = AnomalyClassifier(
            k,
            sketch=FrequentDirections,
            d=m,
            ell=l)

print(f'Model fitting started with {n} training samples, k={k}, l={l}...', file=logf)
classifier.fit(df_train.to_numpy())

# obtain anomaly scores for training set and decide threshold
scores = []
feature_scores_train = []
for _, row in df_train.iterrows():
    (_, score, score_vec) = classifier.classify(row)
    scores.append(score)
    feature_scores_train.append(score_vec)

#  classification threshold
threshold = np.percentile(scores, threshold_p)
print(f'Classification threshold set to : {threshold}', file=logf)

# Classify dataset containing anomalies
test_scores = []
classes = []
elapsed = []
feature_scores = []
for _, row in df_test.iterrows():

    # Sanity check: NaN and inf values
    if np.isnan(row).any() or np.isinf(row).any():
        print(f"❌ {directory}, NaN or inf values found in row: {row.name}")
        continue

    start = timer()
    try:
        # Sanity: keep only first m feature (prevents error if we added other columns to the test set (e.g., labels) --
        (c, score, score_vec) = classifier.classify(row[:m], th=threshold, eta=eta)
    except Exception as e:
        print(f"❌ {directory}, error during classification:", e)
        raise e
    
    end = timer()
    elapsed.append(end - start)
    test_scores.append(score)
    classes.append(c)
    feature_scores.append(score_vec)

df_test['score'] = test_scores
df_test['predicted'] = classes


if task != "dynamic_sampling":
    if save_to_disk is not None:
        df_test[['label', 'predicted', 'score']].to_csv(f'{directory}/classification.csv')

    print('Average inference time: %f [ms]' % (np.mean(elapsed) * 1000), file=logf)

    plot_score_distribution(
        {'key': 'training', 'values': scores}, 
        {'key': 'test', 'values': test_scores},
        f=directory + '/score_distribution' if save_to_disk is not None else None)

    #%%
    # plot feature score
    #from_ = anomalies[0][0]
    #to_ = anomalies[0][1]
    import matplotlib.dates as mdates
    ascoredf = pd.DataFrame(feature_scores)

    top10_metrics = pd.DataFrame(
        ascoredf.abs().max().sort_values(ascending=False).head(3), 
        columns=['score'])

    top10_metrics['desc'] = col_name_to_metric(top10_metrics.index.values, COL_DESC_FILE)

    #leg = ['kube_pod_status_phase', 'container_file_descriptors', 'container_sockets']
    fig = plt.figure(figsize=(3,1.5), dpi=300)
    ascoredf[top10_metrics.index.values].abs().plot.line(ax=fig.gca())
    #plt.gca().get_legend().remove()
    #plt.title('Top-10 absolute scores')
    plt.legend()
    #plt.legend(leg, ncol=3, bbox_to_anchor=(0.5, 1.), fontsize=6)
    #plt.legend(ncol=5, loc='upper center', bbox_to_anchor=(0.5, -0.2))
    # I want to reduce number of datetime ticks on x axis, only 3

    plt.ylabel('Anomaly score')
    plt.xlabel('Time of Day')
    plt.xlim(df_test.index[0], df_test.index[-1])

    plt.show()
    if save_to_disk is not None:
        mysavefig(f'{directory}/top_metrics', bbox_inches='tight', verbose=False)
        top10_metrics.to_csv(f'{directory}/top10_metrics.csv')
    else:
        plt.show()

    #%%
    # PR curve (as likely classes are unbalanced)
    plot_precision_recall(df_test.label.values, test_scores, f=directory + '/precision_recall' if save_to_disk is not None else None)

    #%%
    # plot scores over time
    #plt.figure()
    ax = df_test[df_test['score'] > threshold].plot.line(
        y='score', 
        style='*', 
        color='r',
        label='Anomalous')
    df_test.plot.line(
        y='score', 
        ax=ax,
        label='Not anomalous')
    for a in anomalies:
        plt.axvspan(a[0], a[1], facecolor='r', alpha=0.2)
    #myFmt = mdates.DateFormatter('%H:%M')
    #plt.gca().xaxis.set_major_formatter(myFmt)
    plt.legend(loc='lower right')
    plt.xlim(df_test.index[0], df_test.index[-1])
    plt.ylabel('Anomaly Score')
    plt.title(f'k={k},l={l},\\eta={eta},thresh={threshold:.10f}')
    if save_to_disk is not None:

        mysavefig(f'{directory}/scores', bbox_inches='tight', verbose=False)
    else:
        plt.show()


    #%% store accuracy metrics
    f1 = f1_score(df_test.label.values, df_test.predicted.values)
    precision = precision_score(df_test.label.values, df_test.predicted.values)
    recall = recall_score(df_test.label.values, df_test.predicted.values, zero_division=np.nan)
    accuracy = accuracy_score(df_test.label.values, df_test.predicted.values)
    tn, fp, fn, tp = confusion_matrix(df_test.label.values, df_test.predicted.values, labels=[0, 1]).ravel()
    fpr = fp / (fp + tn)

    with open(f'{directory}/results.csv', 'w') as fres:
        print('k,l,threshold,eta,service,f1,precision,recall,accuracy,fpr', file=fres)
        print(','.join([str(x) for x in [
                k,
                l,
                threshold_p,
                eta,
                SERVICE,
                f1,
                precision,
                recall,
                accuracy,
                fpr]
            ]),file=fres)

    # close log file
    logf.close()




#%%

###### plot metrics task to display metric values and anomaly score over time
if task == 'plot_metrics':
    data = df_test
    ids = [40]

    for ID in ids:
        data.plot.line(
            y=f'value_{ID}', 
            label=f'metric {ID}',
            style=':')
    plt.legend()
    plt.show()
###### 





#%% dynamic frequency sampling
if task == 'dynamic_sampling':
    
    value_cols = []
    for x in df_test.columns:
        if 'value' in x:
            value_cols.append(x)

    df = df_test.copy()
    df['sampled'] = False

    # every 30 seconds we always sample with a baseline
    idx = df.resample('30s', closed='left', label='left').first().index
    df.loc[idx, 'sampled'] = True

    #baseline = df.loc[idx,:]
    #baseline.plot.line(y='value_40', style='.-')

    # here is the sampling logic
    df.loc[df['predicted'], 'sampled'] = True

    # here we discard samples when not predicted, so df contains result after sketch
    df.loc[df['sampled'] == False, value_cols] = np.nan
    df = df.fillna(method='bfill')
    
    # plot sampled version of the signal
    #df.plot.line(y='value_40', style='.-')
    #plt.show()

    #%% 
    # should generalize this to all signals and plot the average vs 
    # the bandwidth that we would use for different thresholds
    from scipy import signal

    ratios = []
    num_samples = []
    for v in value_cols:
        
        sig_sampled = df.loc[:'2023-12-04 10:56:00+01:00',v].to_numpy()
        sig = df_test.loc[:'2023-12-04 10:56:00+01:00',v].to_numpy()

        corr = signal.correlate(sig_sampled, sig)
        autocorr = signal.correlate(sig, sig)
        lags = signal.correlation_lags(len(sig), len(sig_sampled))
        lag0 = np.where(lags == 0)[0]
        ratio =  corr[lag0] / autocorr[lag0]
        ratios.append(ratio[0])

        # this is equal for all metrics
        num_samples.append(df.loc[:'2023-12-04 10:56:00+01:00','sampled'].sum())

    # directory_s = f'{save_to_disk}/{SERVICE}/k{k}_l{l}/'
    # if not os.path.exists(directory_s):
    #     os.makedirs(directory_s)
    # print('Writing to ', directory_s)
    res = pd.DataFrame({
        'correlations': ratios,
        'num_samples': num_samples,
        'metric': value_cols,
        'threshold': threshold_p})
    res.dropna(inplace=True)
    res.to_csv(f'{directory}/ratios-threshold-{threshold_p:.1f}.csv')

    #%% plot sampled values
    #df.loc[df['sampled'], 'value_65'].plot.line(ls='-', marker='o')
    #plt.show()

#%%
"""
    - Plots the list of metrics specified in IDs
    (you probably then need to adjust the legends)
    - On the other axis plot the anomaly score, and highlights in
    red the anomalous points
"""

if task == 'plot_metrics_hpa':
    AID=None
    fig, ax1 = plt.subplots(figsize=(5,2.5))
    #ax2 = ax1.twinx()
    
    if AID is not None:
        data = df_test[anomalies[AID][0]:anomalies[AID][1]]
    else:
        data = df_test

    # plot metric value
    for ID in ids:
        data.plot.line(
            y=f'value_{ID}', 
            ax = ax1,
            style=':',
            label='load',
            color='dodgerblue')
    #ax1.legend(bbox_to_anchor=(0.2, 1.2))
    handles1,labels1 = ax1.get_legend_handles_labels()

    ax2 = data[data['score'] > threshold].plot.line(
        y='score', 
        style='*', 
        color='r',
        label='anomalous',
        secondary_y=True,
        ax=ax1) # notice here ax1, means we use secondary axis starting from here
    
    # plot score
    data.plot.line(
        y='score',
        color='gray',
        lw = 0.75,
        secondary_y=True,
        label='score',
        ax=ax2)
   # ax2.legend(bbox_to_anchor=(0.62, 1.2), loc='upper center', ncol=2)
    
    handles2,labels2 = ax2.get_legend_handles_labels()

    plt.axhline(threshold, color='k', ls=':', lw=1.5)

    ax1.set_ylabel('Normalized CPU')
    ax2.set_ylabel('Anomaly Score')
    ax1.set_xlabel('Collection Timestamp')
    #ax1.legend(bbox_to_anchor=(0.1, 1.2), loc='upper center', ncol=1)
    
    # we join all handles so that we manage a single legend object
    ax1.legend(handles1+handles2, 
               labels1+labels2, 
               ncol=3,
               bbox_to_anchor=(1.05, 1.2))

    #plt.title(f'Anomaly Interval #{AID}')
    #ax2.set_ylabel('score')
    if save_to_disk is not None:
        mysavefig(f'{directory}/fig9', bbox_inches='tight', verbose=False)
    else:
        plt.show()