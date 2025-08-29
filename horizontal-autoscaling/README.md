# Overview

This folder contains code to reproduce Fig.9 of the paper (behavior of MicroView in the presence of HPA).

We use a simple `php-apache` container acting as a frontend web server. The Horizontal Pod Autoscaler (HPA) is configured to scale the number of pods based on CPU usage.

## Reproduce sketch analysis (~5 minutes)

The folder `artifacts/metrics` contains the metrics dataset for this experiment. 

The file `artifacts/metrics/column_desc_test.json` contains the Prometheus query used to collect every metric.

For running the sketch configuration used for this experiment, execute:
```bash
> python ./usecases/postprocessing/classify_pod_metrics.py --task plot_metrics_hpa -s php-apache -l 50 -k 12 -th 99.9 -d ./horizontal-autoscaling/artifacts --learning-rate 0 --ids 12
```

You then obtain `artifacts/results` folder. Within the folder, look for the files `fig9.png` and `top_metrics.png`.

**NOTE**: `top_metrics.png` will have a legend with the top-3 metrics numerical identifiers. To map the names to the actual Prometheus name (as in the paper's legend), use:


```bash
> cat horizontal-autoscaling/artifacts/metrics/php-apache/column_desc_test.json | jq | grep 70 -B 3

{
    "phase": "Failed",
    "query": "sum(kube_pod_status_phase{namespace='hpa-walkthrough', pod=~'php-apache-.*'}) by (phase)",
    "key": 70
```

For example, in the above, `70` corresponds to the number of failed pods.

## Reproduce workload


### Important
Unfortunately, this experiment was run manually for the evaluation in the paper. 
We provide the instructions below to reproduce, but keep in mind the workflow here is not fully stable. 
We are working on automation for this part, please follow-up on HotCRP.

#### Time estimate: ~1h computation time + 30 minutes human time for setup

To reproduce the workload generation and HPA behavior. It involves:

- setting an upper bound in the number of `Allocatable` pods on a Kubernetes worker node
- deploying the `php-apache` web server with HPA enabled
- deploying a load generator that gradually increases the load of requests over time


### Manual instructions
Add `taint` to node to make sure only these pods run on it

```
kubectl taint nodes mcnode18 hpa-experiment:NoExecute
kubectl taint nodes mcnode18 hpa-experiment:NoSchedule
```

Verify with:
```
kubectl get pods --all-namespaces -o wide --field-selector spec.nodeName=<node>
```

Remember to add `tolerations` to all pods relative to this experiment.

Next set maximum allowed pods on the node. Add the entry `maxPods: 6` to the kubelet configuration file `/var/lib/kubelet/conf.yaml`. Restart the kubelet and verify the configuration took place

```
kubectl describe nodes mcnode18 | grep Allocatable -A 6
```

You are now ready to run the experiment. Make sure you have added tolerations and node affinity.

Deploy a sample php apache web-server. Then create load generators. This will deploy a load generator applying the two specified values.yaml files
```
helm upgrade -i loadgenerator-step . -f values.yaml -f values-step.yaml
```

You can tweak the desired duration in `values-step.yaml` (variable `TIME_LIMIT`) and the desired load increase rate (variable `STEP_LOAD`).
Default is `1h`.

Next, watch HPA as follows:
```
kubectl get hpa --watch
```

Delete the load generator object:
```
helm delete loadgenerator-step
```

After the experiment you may want to clean-up resources by deleting all failed Pods
```
kubectl delete pods --field-selector status.phase=Failed
```

### Metrics collection

To collect the metrics dataset, refer to the script `run-collection.sh` in this folder and edit the variables depending on your experiment time.

### Analysis

Refer to the first section.
