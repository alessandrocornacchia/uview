#!/bin/bash

# The script donwloads traces and metrics relative to a given time interval. It also
# produces sampled versions of the traces. 

# express the time in Europe/Rome timezone for convenience
END_TIME="2024-11-08 12:10:00 UTC$(TZ=Asia/Riyadh date +%:::z)"
DURATION="60"
TRAIN_START_TIME="2024-11-08 11:10:00"
TRAIN_END_TIME="2024-11-08 11:30:00"
TEST_START_TIME=$TRAIN_END_TIME
TEST_END_TIME="2024-11-08 12:10:00"
METRICS_DIR="/home/temp/$USER/uview/horizontal-autoscaling/metrics"

cd "/home/temp/$USER/uview/horizontal-autoscaling/"
    
CMD=(
"python" 
"./prometheus-metrics.py"
"--end" "\"${END_TIME}\""
"-d" "$DURATION"
"--train-start" "\"${TRAIN_START_TIME}\""
"--train-end" "\"$TRAIN_END_TIME\""
"--test-start" "\"$TEST_START_TIME\""
"--test-end" "\"$TEST_END_TIME\""
"--pod" "php-apache"
"--directory" "\"$METRICS_DIR\""
)

if [ $# -eq 1 ] && [ $1 == "--dry-run" ] ; then
    echo "${CMD[@]}"
else
    eval "${CMD[@]}"
fi