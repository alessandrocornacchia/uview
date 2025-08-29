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

To deploy containers, `docker` and `docker compose` are required.
Check if they are installed by running:
```bash
docker --version
docker compose version
```


## Plot only
Under the folder `data` we provide the paper's measurements.

You can plot the data either using the Jupyter notebook `plot.ipynb` or directly by running `python plot.py`.

We suggest attaching a VSCode instance with remote SSH and install the [Jupyter extension](https://code.visualstudio.com/docs/datascience/jupyter-notebooks) if you decide to run the notebook version

## Re-run (~ 1h)

To fully reproduce the experiments and collect new measurements you need to run 
```
python run.py
``` 

This will reproduce all scenarios of the figure. 

**NOTE** : To avoid biasing gthe measurements, ensure you are not running other workloads (e.g., other containers) on the machine. 
If you had started containers within a docker compose file before the experiment, flash a `docker compose down`. To kill other running docker containers `docker kill $(docker ps -q)`.

Should you change the parameters, you directly edit the relevant variables in `run.py`.

