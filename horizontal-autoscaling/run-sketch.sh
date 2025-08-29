#!/bin/bash

# This script schedules the execution of metrics_experiments.py for all the combinations of 
# parameters specified in the script.

# ----------------- parameters -----------------
dry_run=1
timeframe='202311081036-202311081100'

if [ $# -eq 1 ]; then
    timeframe=$1
fi

if [ $(hostname) == "mcnode17" ]; then
    workdir="/data/scratch/cornaca/hpa/metrics"
    resdir="/data/scratch/cornaca/hpa/results"
else
    workdir="./"
    resdir="./results"
fi

Ls=(25 50)
Ks=(10 15 20 30)
Ths=(99 99.9)
Etas=(0 0.1 1)
Pods=(
    'php-apache'
)

# make sure to pull latest updates from server before running experiments
#if [ $(hostname) != "mcnode17" ]; then
#    echo "Running from remote, download traces and metrics from mcnode17"
#    rsync -azhP mcnode17:/data/scratch/cornaca/datasets/traces/${timeframe}/ ./datasets/traces/${timeframe} &> /dev/null
#    rsync -azhP mcnode17:/data/scratch/cornaca/datasets/metrics/${timeframe}/ ./datasets/metrics/${timeframe} &> /dev/null
#fi

# ----------------- run -----------------

for p in ${Pods[@]} ; do
    for l in ${Ls[@]} ; do
        for k in ${Ks[@]} ; do
            for th in ${Ths[@]} ; do
                for eta in ${Etas[@]} ; do
                    # if k larger than l continue
                    if [ $k -gt $l ]; then
                        continue
                    fi
                    
                    if [ $dry_run -eq 1 ]; then
                        echo python3 ./classify_pod_metrics.py -s "$p" \
                        -t "$timeframe" \
                        -l $l \
                        -k $k \
                        -w "$resdir" \
                        -th $th \
                        -d "$workdir" \
                        --learning-rate "$eta"
                    else
                        eval python3 ./classify_pod_metrics.py -s "$p" \
                        -t "$timeframe" \
                        -l $l \
                        -k $k \
                        -w "$resdir" \
                        -th $th \
                        -d "$workdir" \
                        --learning-rate "$eta"
                    fi
                done
            done
        done
    done
done
