# Performance Anomaly Injector

Performance anomaly injector consists of a set of contentious microbenchmark targeting at different types of shared resources. It can be used to inject performance anomalies caused by shared resource interference and the interference timing, intensity or/and core location are configurable. Types of shared resources include CPU, memory bandwidth, LLC bandwidth, network bandwidth and I/O bandwidth.

## Build and run on example container

```
cd ~/llm-micro/anomaly-injector
docker build . -t build-image:0.0.1
docker run --rm -v ./:/anomaly -w /anomaly build-image:0.0.1 ./cpu 20
```