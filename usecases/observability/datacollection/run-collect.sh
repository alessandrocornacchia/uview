#!/bin/bash

############### 
# The script triggers collection of traces and metrics relative to a given time interval. 
# After execution, it delivers csv files with metrics and traces and also produces sampled versions of the traces using head-based sampling.
############### 

if [ $# -lt 1 ]; then
    echo "Usage: $0 <experiment_id>"
    exit 1
fi

export EXPERIMENT_ID=$1

# *************** SCRIPT PARAMETERS (defaults) ********************
APP_DEFAULT='dsb_hotel'
BASEDIR="$APP_DIR/$APP"

# enable/disable collection of these
START_TIME_DEFAULT="2024-09-09 19:57:00"
END_TIME_DEFAULT="2024-09-09 19:58:00"
LOOKBACK_MINUTES_DEFAULT="30"
# ******************************************************


TZ="UTC$(TZ=$UTC_OFFSET_ZONE date +%:::z)"

### Step 1. Get configuration from environment variables is they are set, else use default above
START_TIME_TZ="$EXPERIMENT_START_TS"
END_TIME_TZ="$END_INJECT_TS"

# if the above are not set, use the default
if [ -z "$END_INJECT_TS" ]; then
    echo "⚠️ END_INJECT_TS is unset, using hardcoded end time"
    END_TIME_TZ="$END_TIME_DEFAULT $TZ"
fi

if [ -z "$EXPERIMENT_START_TS" ]; then
    echo "⚠️ EXPERIMENT_START_TS is unset, using hardcoded start time"
    START_TIME_TZ="$START_TIME_DEFAULT $TZ"
fi

# log the configuration
echo "Requested start time: $START_TIME_TZ"
echo "Requested end time: $END_TIME_TZ"

# random sampling percentage (sample x% of the collected traces)
PERCENTAGE_SAMPLE="1 5 20 100"

# output directories: be better to use data scratch volumes here
METRICS_DIR="$DATASET_DIR/$EXPERIMENT_ID/metrics"
TRACES_DIR="$DATASET_DIR/$EXPERIMENT_ID/traces"

# time resolution in seconds
TIME_RESOLUTION=1

# ******************************************************

# move in the directory of this script if not already
cd "$(dirname "$0")"

# get all service names as defined by the wiring spec
SVC=(
    $(cat $BASEDIR/wiring/specs/original.go | egrep -o "\"[^\"]*_service\"" | uniq)
)


# downlaod traces and produce sampled versions
python ./jaeger_traces.py --jaeger-endpoint "$JAEGER" --service "unknown_service:frontend_service_process" --end "$END_TIME_TZ" --start "$START_TIME_TZ" -D $TRACES_DIR -y download

echo "Sampling traces..."
for p in $PERCENTAGE_SAMPLE ; do
    echo "==> sampling $p%"
    python ./jaeger_traces.py --service "unknown_service:frontend_service_process" --end "$END_TIME_TZ" --start "$START_TIME_TZ" -D $TRACES_DIR sample -p $p
done

    
echo "Start metrics collection.."
echo "Collecting metrics for services: ${SVC[@]}. Confirm? [y/n]"

# uncomment to have interactive
# read CONFIRM
# if [ $CONFIRM != "y" ] ; then
#     echo "Aborted."
#     exit 1
# fi

for Service in "${SVC[@]}" ; do
    # build command (it uses a default metric_config.yaml file for metric configuration)
    CMD=(
    "python" 
    "./prometheus-metrics.py"
    "--endpoint" "\"$PROMETHEUS\""
    "--end-time" "\"$END_TIME_TZ\""
    "--start-time" "\"$START_TIME_TZ\""
    "-r $TIME_RESOLUTION"
    "--service" "$Service"
    "--directory" "\"$METRICS_DIR\""
    "--config" "\"./metric_config.yaml\""
    )

    # dry-run only prints
    if [ $# -eq 2 ] && [ $2 == "--dry-run" ] ; then
        echo "${CMD[@]}"
    else
    # run it
        eval "${CMD[@]}"
    fi

    done

exit 0