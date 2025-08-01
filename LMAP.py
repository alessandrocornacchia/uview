import copy
import logging
import os
import threading
import time
from typing import Dict, List, Tuple, Any, Optional, Callable

import numpy as np
from classifiers.autoencoders import VAE
from classifiers.statistical import ThresholdAnomalyDetector
from metrics import METRIC_TYPE_COUNTER, METRIC_TYPE_GAUGE, MetricsPage
from rdma.helpers import MRMetadata, OneSidedReader, QueuePairPool
from classifiers.enums import Models
from classifiers.classifiers import ModelBuilder, SubspaceAnomalyDetector
from prometheus_client.core import REGISTRY, CounterMetricFamily, GaugeMetricFamily
from defaults import DEFAULT_POLL_INTERVAL

class LMAP:
    """
    Local Metrics Processing Pipeline (LMAP).
    Each LMAP instance is responsible for collecting metrics from a subset of memory regions.
    Processing them with anomaly detector
    Ensuring compatibility with Prometheus format.
    """
    
    models = {
        Models.FREQUENT_DIRECTION_SKETCH: SubspaceAnomalyDetector,
        Models.VAE: VAE,
        Models.THRESHOLD: ThresholdAnomalyDetector 
    }
    
    def __init__(self, collector_id: str,
                 control_info: List[List[Dict]],
                 rdma: OneSidedReader,
                 scrape_interval: int,
                 start_timestamp: Optional[float] = None):
        """
        Initialize the LMAP collector
        
        Args:
            collector_id: Identifier for this collector
            control_info: Control info for all memory regions
            rdma: RDMA object for communication
            scrape_interval: Interval for scraping metrics
            start_timestamp: Optional timestamp for when the collection starts
        """
        self.collector_id = collector_id
        self.control_info = control_info
        self.rdma = rdma
        self.scrape_interval = scrape_interval
        self.start_t = start_timestamp
        self.running = False
        self.thread = None
        self.logger = logging.getLogger(f'MicroviewNIC.{collector_id}')
        self.statistics = {}
        self.classifiers: Dict[str, Any] = {}
        
        

    def set_classifier(self, model: Models, **kwargs: Any):
        """
        Set the classifier for all pods
        """
        
        kwargs["model"] = model
        self.logger.info(f"Classifiers set for pods: {model}")
        for mr in self.control_info:
            for ci in mr:
                pod_id = ci["pod_id"]
                # TODO something not correct here?
                kwargs["num_metrics"] = ci["num_metrics"]
                self.logger.info("Setting classifier for pod %s with %d metrics", pod_id, kwargs["num_metrics"])
                try:
                    c = LMAP.models[model].build(**kwargs)
                    self.classifiers[pod_id] = c
                except KeyError:
                    raise ValueError(f"Unknown model type: {model}")
                except Exception as e:
                    self.logger.error(f"Error building classifier for pod {pod_id}: {e}")
                    raise e
        

    def _read_metrics(self) -> Dict[str, List[MetricsPage]]:
        """
        Read metrics from assigned memory regions using RDMA
        """
        # Execute one RDMA read operation from all active memory regions
        results = self.rdma.execute()
        metrics: Dict[str, List[MetricsPage]] = {}

        # Loop over memory regions
        for i in range(len(results)):
            # This is now one MR
            data_region = results[i]
            # This is the corresponding control information
            control_region = self.control_info[i]
            
            # Loop over pages in the memory region
            for j in range(len(control_region)):
                pod_id = control_region[j]["pod_id"]
                page_occupancy = control_region[j]["num_metrics"]
                page_size_bytes = control_region[j]["page_size_bytes"]
                
                # Read page data
                raw_page = data_region[j*page_size_bytes:(j+1)*page_size_bytes]   
                
                self.logger.debug(f"📊 LMAP {self.collector_id} reading page {j} for pod {pod_id} with occupancy {page_occupancy}")
                
                # Parse metrics from page
                mp = MetricsPage.from_bytes(raw_page, page_occupancy)
                
                # Add metrics to collection
                metrics.setdefault(pod_id, []).append(mp)

        return metrics
    

    def _read_metric_values(self) -> Dict[str, np.ndarray]:
        """
        Read metrics and return only values, should avoid some Python loops
        """
        # Execute one RDMA read operation from all active memory regions
        results = self.rdma.execute()
        metrics: Dict[str, MetricsPage] = {}

        # Loop over memory regions
        for i in range(len(results)):
            # This is now one MR
            data_region = results[i]
            # This is the corresponding control information, one CR per MR
            control_region = self.control_info[i]
            
            # Loop over pages in the memory region
            for j in range(len(control_region)):
                pod_id = control_region[j]["pod_id"]
                page_occupancy = control_region[j]["num_metrics"]
                page_size_bytes = control_region[j]["page_size_bytes"]
                
                # Read page data
                raw_page = data_region[j*page_size_bytes:(j+1)*page_size_bytes]   
                
                self.logger.debug(f"📊 LMAP {self.collector_id} reading page {j} for pod {pod_id} with occupancy {page_occupancy}")
                
                # Parse values from page
                values = MetricsPage.from_bytes(raw_page, page_occupancy).get_metrics_values()
                
                # Add metrics to collection
                metrics.setdefault(pod_id, []).append(values)

        # Perform concatenation once per pod rather than repeatedly
        values: Dict[str, np.ndarray] = {}
        for pod_id in metrics:
            if len(metrics[pod_id]) > 1:
                values[pod_id] = np.concatenate(metrics[pod_id])
            else:
                values[pod_id] = metrics[pod_id][0]

        return values
    
    
    def collect(self):
        """
        Collect metrics for Prometheus
        
        Returns:
            List of Prometheus metrics
        """
        prom_metrics = []
        
        try:
            # Read metrics using RDMA
            self.logger.debug(f"🔭 LMAP {self.collector_id} received scrape request, starting metrics reading")
            metrics_pages = self._read_metrics()
            
            # Loop over pods
            for pod_id, pages in metrics_pages.items():
                # Loop over pages
                for p in pages:
                    # Loop over metrics
                    # Get the three arrays from get_metrics()
                    names, types, values = p.get_metrics()
                    for metric_name, metric_type, value in zip(names, types, values):
                        
                        # Process raw metrics into Prometheus format
                        if metric_type == METRIC_TYPE_COUNTER:
                            metric = CounterMetricFamily(
                                name=f"{self.collector_id}_{metric_name}",  # TODO dirty trick to have same registry export same metric name
                                documentation=f"Counter metric {metric_name}",
                                labels=['pod_id', 'collector_id']
                            )
                        elif metric_type == METRIC_TYPE_GAUGE:
                            metric = GaugeMetricFamily(
                                name=f"{self.collector_id}_{metric_name}", # TODO dirty trick to have same registry export same metric name
                                documentation=f"Gauge metric {metric_name}",
                                labels=['pod_id', 'collector_id']
                            )
                        
                        # Add pod_id and collector_id as labels
                        metric.add_metric([pod_id, self.collector_id], value)
                        prom_metrics.append(metric)
                
        except Exception as e:
            self.logger.error(f"⛔️ Error collecting metrics in LMAP {self.collector_id}: {e}")
        
        return prom_metrics
    

    def start_local_scrape_loop(self, cpu_core: Optional[int] = None):
        """
        Start a dedicated thread for local metrics reading
        """

        def scrape_loop():
            
            if self.start_t is None:
                self.start_t = time.time()

            self.logger.info(f"LMAP {self.collector_id}, scrape loop interval={self.scrape_interval}s, thread id {threading.get_native_id()}, start time {self.start_t}")
            
            # set thread affinity if CPU core is not none
            if cpu_core is not None:
                try:
                    # Get thread ID and set affinity directly
                    os.sched_setaffinity(0, {cpu_core})  # 0 means current thread
                    self.logger.info(f"LMAP {self.collector_id} pinned to CPU core {cpu_core}")
                except Exception as e:
                    self.logger.warning(f"Failed to pin thread to core {cpu_core}: {e}")
            
            self.statistics["num_scrapes"] = 0
            scrapes_i = 0
            num_partials = 0
            last_partial_time = self.start_t
            
            while self.running: # TODO this is not useful without lock...
                try:
                    # Read metrics
                    metrics = self._read_metric_values()
                    self.logger.debug(f"📊 LMAP {self.collector_id} read metrics: {metrics}")
                    
                    # Assign metrics to correct classifier
                    for pod_id, pod_metrics in metrics.items():
                        
                        # Run the pod classifier if present
                        c = self.classifiers.get(pod_id)
                        
                        if c:
                            # log dimension
                            self.logger.debug(f"LMAP {self.collector_id} classifying pod {pod_id} with {pod_metrics.shape} metrics")
                            c.classify(pod_metrics)
                            
                
                    # Update statistics
                    # TODO can go on a function itself                    
                    if len(metrics): 
                        # successful scrape (at least one pod)
                        _now = time.time()
                        self.statistics["num_scrapes"] += 1
                        self.statistics["time_total"] = _now - self.start_t
                        
                        # every 30 secs elapsed, record partial scraping rates
                        if self.statistics["time_total"] // 10 >= num_partials:
                            elapsed = _now - last_partial_time
                            delta  = self.statistics["num_scrapes"] - scrapes_i
                            self.statistics[f"scrape_rate_{num_partials}"] = delta / elapsed
                            logging.info(f"LMAP {self.collector_id} scrape rate: {self.statistics[f'scrape_rate_{num_partials}']:.2f} scrapes/s")
                            scrapes_i = self.statistics["num_scrapes"]
                            last_partial_time = _now
                            num_partials += 1
                            
                        self.statistics["end_time"] = time.time()

                    # Wait for next iteration
                    if self.scrape_interval > 0:
                        time.sleep(self.scrape_interval)
                
                except Exception as e:
                    self.logger.error(f"Error in LMAP {self.collector_id} scrape loop: {e}")
                    raise e
        
        self.running = True
        self.thread = threading.Thread(target=scrape_loop, name=f"LMAP-{self.collector_id}")
        # self.thread.daemon = True  # Thread will exit when main program exits
        self.thread.start()
        self.logger.info(f"LMAP {self.collector_id} scrape thread started")


    def stop_local_scrape_loop(self):
        """Stop the local scrape loop thread"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
            self.logger.info(f"LMAP {self.collector_id} scrape thread stopped")
            self.thread = None


    def dump_statistics(self, filename: Optional[str] = None):
        """Dump statistics to logger"""
        self.logger.debug(f"LMAP {self.collector_id} statistics: {self.statistics}")
        
        for key, value in self.statistics.items():
            if isinstance(value, list):
                self.statistics["Average" + key] = np.mean(value)
                self.statistics["Max" + key] = np.max(value)
                self.statistics["Min" + key] = np.min(value)
                self.statistics["Std" + key] = np.std(value)
                del self.statistics[key]


        if filename:
            # write to csv
            with open(filename, 'w') as f:
                for key, value in self.statistics.items():
                    f.write(f"{key},{value}\n")
        
        self.logger.info(f"=========== {self.collector_id} ==============")
        self.logger.info("Key\tValue")
        self.logger.info("=====================================")
        for key, value in self.statistics.items():
            self.logger.info(f"{key}\t{value}")
        self.logger.info("=====================================")


    def cleanup(self):
        """Clean up resources"""
        self.logger.info(f"Cleaning up LMAP {self.collector_id}")
        self.stop_local_scrape_loop()
        self.dump_statistics(f"stats_{self.collector_id}.csv")
        if not self.running and self.rdma:
            self.rdma.cleanup()
            self.rdma = None
        self.logger.info(f"LMAP {self.collector_id} cleaned up")

    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()