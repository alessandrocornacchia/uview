# This script reads a dataset from a csv file and splits it into a training and test set to be input to uView
#%%
import pandas as pd
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--id-exp", "-e", type=str, help="Experiment ID", required=False)
args = parser.parse_args()

experiment_id = args.id_exp

# get folders in directory ../datasets/metrics/202409091926-202409091958/
datasetdir = os.environ.get('DATASET_DIR', './datasets')
timezone = os.environ.get('UTC_OFFSET_ZONE', 'Asia/Riyadh')

service_folders = [os.path.join(f'{datasetdir}/{experiment_id}/metrics', f) 
           for f in os.listdir(f'{datasetdir}/{experiment_id}/metrics') 
           if os.path.isdir(os.path.join(f'{datasetdir}/{experiment_id}/metrics', f))]


train_start_time = os.environ.get('EXPERIMENT_START_TS', '2024-09-09 19:26:00')
train_end_time = os.environ.get('START_INJECT_TS', '2024-09-09 19:40:00')
test_start_time = os.environ.get('START_INJECT_TS', '2024-09-09 19:40:00')
test_end_time = os.environ.get('END_INJECT_TS', '2024-09-09 19:58:00')

print(f'Experiment ID: {experiment_id}, splitting dataset into train and test sets')
print(f'train_start_time: {train_start_time}')
print(f'train_end_time: {train_end_time}')
print(f'test_start_time: {test_start_time}')
print(f'test_end_time: {test_end_time}')    

#%%
for f in service_folders:
    print(f)
    
    try:
        df = pd.read_csv(f'{f}/data.csv', parse_dates=['timestamp'], index_col='timestamp')
    except FileNotFoundError:
        print(f'{f}/data.csv not found')
        continue
    
    # convert timestamp to desired timezone
    df.index = df.index.tz_convert(timezone)
    
    df_train = df.loc[train_start_time:train_end_time]
    df_test = df.loc[test_start_time:test_end_time]

    # sanity check
    assert len(df_train) > 0
    assert len(df_test) > 0

    # write to train and test files
    df_train.to_csv(f'{f}/data_train.csv')
    df_test.to_csv(f'{f}/data_test.csv')

    print(df_train.shape)
    print(df_test.shape)

    # copy column_desc.json file to column_desc_train.json and column_desc_test.json
    os.system(f'cp {f}/column_desc.json {f}/column_desc_train.json')
    os.system(f'cp {f}/column_desc.json {f}/column_desc_test.json')
