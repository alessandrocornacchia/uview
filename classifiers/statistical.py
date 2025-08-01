import numpy as np
from typing import Any, List, Tuple
from classifiers.enums import Models

class ModelBuilder:
    def build(self, num_metrics, **kwargs):
        raise NotImplementedError("ModelBuilder is an abstract class")

class ThresholdAnomalyDetector(ModelBuilder):
    """
    A simple threshold-based anomaly detector that compares metrics against predefined thresholds
    """
    
    def __init__(self, thresholds: np.ndarray = None, bootstrap: bool = False, **kwargs):
        """
        Initialize a threshold-based anomaly detector
        
        Args:
            thresholds: Array of thresholds for each metric
            bootstrap: Whether to initialize with default thresholds
        """
        self.thresholds = thresholds
        
        # Initialize with default thresholds if requested
        if bootstrap and thresholds is None:
            num_metrics = kwargs.get('num_metrics', 10)
            self._bootstrap(num_metrics)
    
    @staticmethod
    def build(**kwargs):
        """Builder method for ThresholdAnomalyDetector
        
        Args:
            num_metrics: Number of metrics to monitor (required)
            default_threshold: Default threshold value for all metrics (optional)
            thresholds: Custom thresholds for each metric (optional)
            bootstrap: Whether to initialize with default thresholds (optional)
            
        Returns:
            ThresholdAnomalyDetector: Configured detector instance
        """
        num_metrics = kwargs.get('num_metrics')
        if num_metrics is None:
            raise ValueError("num_metrics must be provided")
        
        default_threshold = kwargs.get('default_threshold', 3.0)
        thresholds = kwargs.get('thresholds')
        
        if thresholds is None and 'bootstrap' in kwargs and kwargs['bootstrap']:
            thresholds = np.ones(num_metrics) * default_threshold
        
        return ThresholdAnomalyDetector(thresholds=thresholds, **kwargs)
    
    def _bootstrap(self, num_metrics: int):
        """Initialize with default thresholds
        
        Args:
            num_metrics: Number of metrics to monitor
        """
        default_threshold = 3.0  # Default threshold (3 standard deviations)
        self.thresholds = np.ones(num_metrics) * default_threshold
    
    def classify(self, metrics: np.ndarray, **kwargs) -> Tuple[bool, float, np.ndarray]:
        """
        Compare metrics against thresholds to detect anomalies
        
        Args:
            metrics: Array of metric values to check
            
        Returns:
            Tuple containing:
            - is_anomaly: Boolean indicating if sample is anomalous
            - max_score: Maximum deviation score
            - scores: Array of individual metric deviation scores
        """
        if len(metrics) != len(self.thresholds):
            raise ValueError(f"Expected {len(self.thresholds)} metrics, got {len(metrics)}")
        
        # Calculate deviation scores (how much each value exceeds its threshold)
        scores = np.abs(metrics) - self.thresholds
        
        # Consider any value exceeding its threshold as anomalous
        max_score = np.max(scores)
        is_anomaly = max_score > 0
        
        return (is_anomaly, max_score, scores)
    
    def update_thresholds(self, new_thresholds: np.ndarray):
        """Update detector thresholds
        
        Args:
            new_thresholds: New threshold values to use
        """
        if len(new_thresholds) != len(self.thresholds):
            raise ValueError(f"Expected {len(self.thresholds)} thresholds, got {len(new_thresholds)}")
        
        self.thresholds = new_thresholds


if __name__ == "__main__":
    
    # Example usage
    num_metrics = 5
    detector = ThresholdAnomalyDetector.build(num_metrics=num_metrics, bootstrap=True)
    
    # Sample data: normal data
    normal_data = np.random.randn(num_metrics) * 0.5  # Within 3 std deviations
    is_anomaly, score, scores = detector.classify(normal_data)
    print(f"Normal data - Anomaly: {is_anomaly}, Score: {score}")
    
    # Sample data: anomalous data (one value far exceeds threshold)
    anomaly_data = np.random.randn(num_metrics) * 0.5
    anomaly_data[2] = 5.0  # Exceeds default threshold
    is_anomaly, score, scores = detector.classify(anomaly_data)
    print(f"Anomalous data - Anomaly: {is_anomaly}, Score: {score}")