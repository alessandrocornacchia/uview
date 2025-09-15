# Overview

This folder contains code to reproduce Fig.2 of the paper. Refer to the paper for terminology.

The script `run.py` will deploy:
* A set of containers with varying cardinality
* A `cAdvisor` instance co-located with the containers, serving as a metrics generator 
* A `Prometheus` instance to scrape metrics from `cAdvisor` and store them in a time-series database 

We define two time intervals:
- `ingestion` : time interval where `Prometheus` scrapes metrics from `cAdvisor`
- `generation` : time interval at which `cAdvisor` refreshes metrics from the containers by reading from kernel cgroups

### Overheads measurements 
Because we deploy `cAdvisor` as a container itself, its resource usages are also measured. We exploit this fact and collect the CPU cores used by `cAdvisor` to compute the overhead of the metrics collection for the different configurations in Fig.2.

Specifically, at line 127 of `run.py`:

```127| query = "rate(" + metric_query + "{container_label_com_docker_compose_service='cadvisor'}[" +  window  + "])"```


## Prerequisites

Check if 'docker` is installed and if you have the permissions:
```bash
docker --version
docker compose version
```


## Plot only
Under the folder `data` we provide the paper's measurements.

You can plot the data either using the Jupyter notebook `plot.ipynb` or directly by running `python plot.py`.

We suggest attaching a VSCode instance with remote SSH and install the [Jupyter extension](https://code.visualstudio.com/docs/datascience/jupyter-notebooks) if you decide to run the notebook version

## Re-run experiment (~ 2h)

### ⚠️ Important
This is a performance critical experiment, the reviewers are expected to avoid mutual interferences while reproducing the experiment. 
We propose three options:

* **Different nodes**. Each reviewer runs the experiment on a different node, with the following assignment: `aec-nsdi-1@mcnode17`, `aec-nsdi-2@mcnode18`, `aec-nsdi-3@mcnode19`.
Avoid `mcnode28` as it is used for other artifacts. 
* **Different testbed**. Reviewers are also free to use their own testbed. We expect the general trends to hold, however, the absolute values may vary depending on the hardware.
* **Time-sharing**. If reviewers need to share the same node, we suggest to run the experiment at different times of the day with manual LOCK/UNLOCK on HotCRP platform.

If you had started containers within a docker compose file before the experiment, flash a `docker compose down`. To kill other running docker containers `docker kill $(docker ps -q)`.

### Steps
To reproduce the experiment and collect your own measurements, simply run:
```
python run.py
``` 

This will reproduce all scenarios of the figure. 
Should you change the parameters, you directly edit the relevant variables in `run.py`.

