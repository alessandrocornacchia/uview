#!/bin/sh

# This scripts extract a csv file with columns start time , end time and affected service
# for a scheduled chaos experiment. This script extracts information from chaos resources
# and thus has to be run before deleting the chaos experiment (which would delete the resources).
# You can control with the historyLimit parameter in the schedule.yaml file how many chaos resources
# are mantained in the cluster. The default value is 5.
# 
# The script supports both chaos experiment where a container is chosen at random among
# a set of containers, and chaos experiments where a all containers in a set are chosen.
#
# The script tries to stop any scheduled experiment deleting all "schedule" resources

if [ $# -ne 2 ] ; then
    echo "Usage: $0 <chaos_resource> <output file>"
    exit 1
fi

CRD="$1"

# check that CRD is one of "stresschaos", "networkchaos"
if [ "$CRD" != "stresschaos" ] && [ "$CRD" != "networkchaos" ] ; then
    echo "Error: $CRD is not a valid/supported chaos resource"
    exit 1
fi

OUT="$2"
CHAOS_EXPERIMENTS="$(kubectl get ${CRD} -o name)"

echo "start,end,service" > $OUT
for exp in $CHAOS_EXPERIMENTS ; do
    # experiment start time
    START=$(kubectl get $exp -o json | \
    jq '.status.experiment.containerRecords' | \
    jq '[.[] | select(.selectorKey == ".") | .events[] | select(.operation == "Apply")] | .[0].timestamp' | \
    sed 's/"//g')

    # experiment end time
    END=$(kubectl get $exp -o json | \
    jq '.status.experiment.containerRecords' | \
    jq '[.[] | select(.selectorKey == ".") | .events[] | select(.operation == "Recover")] | .[0].timestamp' | \
    sed 's/"//g')

    # pod on which anomaly is has been injected
    POD=$(kubectl get $exp -o json | \
    jq '.status.experiment.containerRecords' | \
    jq '.[] | select(.selectorKey == ".")' | jq '.id' | \
    sed 's/"//g')

    # remove quotes from POD
    for p in $POD ; do
        p=$(echo $p | cut -d '/' -f 2)
        SVC=$(kubectl get po ${p} -o jsonpath='{.metadata.labels.app}')
        # convert time in this format 2023-07-01T18:13:59Z to time in this format 2023-07-01 18:13:59 UTC+0
        START=$(date -d "$START" +"%Y-%m-%d %H:%M:%S%:::z")
        END=$(date -d "$END" +"%Y-%m-%d %H:%M:%S%:::z")        
        echo "$START,$END,$SVC" >> $OUT
    done

done

# Also stops the experiment
kubectl delete schedule --all