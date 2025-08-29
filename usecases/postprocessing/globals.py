import argparse
import os
import sys 
import platform

DATASET_TIMEFRAME = None

# so that we can call all scripts with timerange option from cmd line
if not 'ipykernel_launcher.py' in sys.argv[0]:
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--id-exp", "-e", type=str, help="Experiment ID", required=False)
    args = argparser.parse_args()
    if args.id_exp is not None:
        DATASET_TIMEFRAME = args.id_exp

basedir = '.'
if 'mcnode' in platform.uname().node:
    basedir = os.getenv('DATASET_DIR', '/data/scratch/cornaca')
    
if DATASET_TIMEFRAME is None:
    DATASET_TIMEFRAME = os.environ.get('EXPERIMENT_ID', 'NSDI26') #'NSDI26' #'14Sept0950'