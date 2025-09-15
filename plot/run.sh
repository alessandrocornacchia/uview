#!/bin/bash

# the name of this experiment, used to create sub-direcories with artifacts
export EXPERIMENT_NAME="aec-nsdi"

# IPU hostname
export REMOTE_HOST="mcbf28"

# path to artifacts on the IPU (check tests/benchmarks/tput.py)
export REMOTE_PATH="/home/temp/aec-nsdi-1/uview/results/$EXPERIMENT_NAME"

# local path to store artifacts and figures
export LOCAL_PATH="$HOME/uview/results/$EXPERIMENT_NAME"

# initialize conda environment
source ~/.condainit
conda activate uview

# collect artifacts from IPU, preprocess and store locally
python preprocess.py --download --force --input-path $LOCAL_PATH

# plot fig 5(a)
python tput-vs-classifier.py

# plot fig 5(b)
python tput-with-prometheus.py


