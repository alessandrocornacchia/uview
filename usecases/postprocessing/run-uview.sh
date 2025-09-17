#!/bin/bash


if [ $# -ne 2 ]; then
    echo "Usage: $0 <collect|sketch|trace> experiment_id"
    exit 1
fi

# make sure to export environment variables if not already done

EXPERIMENT_ID=$2
cd ../experiments/$EXPERIMENT_ID
set -a
. .env
cd -

echo $EXPERIMENT_ID

# shortcut to this
# alias pyuview="conda run -n uview --live-stream python"

# experiment start time
# assumptions:
# - both loadgen and anomaly injector have been started at the same time 
# - injector waits a transient period before starting to inject anomalies
# note these are automatically enforced when using orchestrator.py

# these variables will have UTC+00 as timezone, because logs are generated on mcnodes which are in UTC+00 
export EXPERIMENT_START_TS="$(cat $DATASET_DIR/$EXPERIMENT_ID/anomalies.log | head -n 1 | cut -f 1 -d ',') UTC+00"

# 5th anomaly injected
export START_INJECT_TS="$(cat $DATASET_DIR/$EXPERIMENT_ID/anomalies.log | grep "# of targets" | head -n 10 | cut -f 1 -d ',' | tail -n1) UTC+00"

# end of exeperiment after last anomaly is injected
export END_INJECT_TS="$(cat $DATASET_DIR/$EXPERIMENT_ID/anomalies.log | grep "End of anomaly" | head -n 1 | cut -f 1 -d ',') UTC+00"


if [ -z "$CONDA_PREFIX" ]; then
    echo "Activate conda environment first!"
    exit 1
fi

collect() {
    echo "==========================================================="
    echo "Running data collections..."
    echo "==========================================================="
    echo ""
    ../observability/datacollection/run-collect.sh ${EXPERIMENT_ID}

    if [ $? -ne 0 ]; then
        echo "Error running data collections"
        exit 1
    fi

    echo "==========================================================="
    echo "Split into training and test..."
    echo "==========================================================="
    echo ""

    # split the dataset into training and test sets
    python ../observability/datacollection/split.py -e ${EXPERIMENT_ID}
}


sketch_analysis() {
    echo "==========================================================="
    echo "Running sketches over metrics dataset with parallel execution..."
    echo "==========================================================="
    echo ""

    # parameters for the sketches with grid-search
    # ----------------- parameters -----------------

    Ls=(25 50)
    Ks=(10 15 20 30)
    Ths=(99 99.9)
    Etas=(0 0.1 0.01)
    Pods=(
        'productcatalogservice'
        'adservice'
        'cartservice'
        'checkoutservice'
        'currencyservice'
        'emailservice'
        'paymentservice'
        'shippingservice'
        'recommendationservice'
        'redis-cart'
        'frontend'
    )

    # get all service names as defined by the Blueprint wiring spec
    if [[ $EXPERIMENT_ID != *"SockShop"* ]]; then

        Pods=(
            $(cat $APP_DIR/$APP/wiring/specs/$BUILD_NAME.go | egrep -o "\"[^\"]*_service\"" | uniq)
        )

    fi

    # ----------------- run -----------------
    COMMANDS=""

    for p in ${Pods[@]} ; do
        for l in ${Ls[@]} ; do
            for k in ${Ks[@]} ; do
                for th in ${Ths[@]} ; do
                    for eta in ${Etas[@]} ; do
                        # if k larger than l continue
                        if [ $k -gt $l ]; then
                            continue
                        fi    
                        
                        COMMANDS+="python3 ./classify_pod_metrics.py -s "$p" \
                        -t "$EXPERIMENT_ID" \
                        -l $l \
                        -k $k \
                        -th $th \
                        -d "$DATASET_DIR/$EXPERIMENT_ID" \
                        --learning-rate "$eta"\n"

                    done
                done
            done
        done
    done

    echo -e $COMMANDS | python ./parexecute.py
}


vae_analysis() {
    echo "==========================================================="
    echo "Running VAE over metrics dataset with parallel execution..."
    echo "==========================================================="
    echo ""

    python VAE_AD.py --id ${EXPERIMENT_ID}
    python aggregate_VAE.py --id ${EXPERIMENT_ID}

}

hypertuning() {

    echo ""
    echo "====================================="
    echo "Finding optimal configuration for the sketches..."
    echo "====================================="
    echo ""

    python eval-predictions.py -e=${EXPERIMENT_ID}


    echo ""
    echo "====================================="
    echo "Merging metrics classifications using best sketches..."
    echo "====================================="
    echo ""

    python merge.py -e=${EXPERIMENT_ID}

}


tracing_hook() {

    echo "==========================================================="
    echo "Running distributed tracing with sketch support..."
    echo "==========================================================="
    echo ""

    python3 sketch-tracer.py -e=${EXPERIMENT_ID}
}

# parse cmdline argument and run the desired function
case $1 in
    collect)
        collect
        ;;
    sketch)
        sketch_analysis
        ;;
    vae)
        vae_analysis
        ;;
    trace)
        tracing_hook
        ;;
    hypertune)
        hypertuning
        ;;
    all)
        collect
        sketch_analysis
        hypertuning
        tracing_hook
        ;;
    *)
        echo "Usage: $0 <collect|sketch|trace|hypertune|all> experiment_id"
        exit 1
        ;;
esac
