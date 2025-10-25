"""
Performance monitoring and benchmarking utilities.

This module provides tools for monitoring performance metrics,
benchmarking functions, and profiling critical code paths.
"""

import time
import psutil
import threading
from contextlib import contextmanager
from typing import Dict, List, Any, Callable, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Performance monitoring for the matching engine.
    
    Tracks various performance metrics including latency, throughput,
    memory usage, and system resources.
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
        self.start_time = time.time()
        self.lock = threading.Lock()
        
        # System monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
        
        logger.info("Performance monitor initialized")
    
    def record_metric(self, name: str, value: float) -> None:
        """
        Record a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
        """
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(value)
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Increment value
        """
        with self.lock:
            self.counters[name] = self.counters.get(name, 0) + value
    
    def get_metric_stats(self, name: str) -> Dict[str, float]:
        """
        Get statistics for a metric.
        
        Args:
            name: Metric name
            
        Returns:
            Dictionary with min, max, avg, count
        """
        with self.lock:
            if name not in self.metrics or not self.metrics[name]:
                return {"min": 0, "max": 0, "avg": 0, "count": 0}
            
            values = self.metrics[name]
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values)
            }
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        with self.lock:
            return self.counters.get(name, 0)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            return {
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_vms_mb": memory_info.vms / 1024 / 1024,
                "memory_percent": self.process.memory_percent(),
                "cpu_percent": cpu_percent,
                "thread_count": self.process.num_threads(),
                "uptime_seconds": time.time() - self.start_time,
                "memory_growth_mb": (memory_info.rss - self.initial_memory) / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}")
            return {}
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        with self.lock:
            summary = {
                "uptime_seconds": time.time() - self.start_time,
                "counters": dict(self.counters),
                "metrics": {}
            }
            
            for name, values in self.metrics.items():
                if values:
                    summary["metrics"][name] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "count": len(values)
                    }
            
            # Add system stats
            summary.update(self.get_system_stats())
            
            return summary
    
    def reset(self) -> None:
        """Reset all metrics and counters."""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.start_time = time.time()
            self.initial_memory = self.process.memory_info().rss


@contextmanager
def measure_latency(monitor: PerformanceMonitor, operation_name: str):
    """
    Context manager to measure operation latency.
    
    Args:
        monitor: Performance monitor instance
        operation_name: Name of the operation being measured
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        latency_ms = (time.perf_counter() - start_time) * 1000
        monitor.record_metric(f"{operation_name}_latency_ms", latency_ms)


def benchmark_function(func: Callable, *args, **kwargs) -> Dict[str, float]:
    """
    Benchmark a function execution.
    
    Args:
        func: Function to benchmark
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Dictionary with timing statistics
    """
    times = []
    iterations = 100  # Default iterations
    
    # Warm up
    for _ in range(10):
        try:
            func(*args, **kwargs)
        except:
            pass
    
    # Benchmark
    for _ in range(iterations):
        start_time = time.perf_counter()
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in benchmark: {str(e)}")
        finally:
            times.append((time.perf_counter() - start_time) * 1000)
    
    if not times:
        return {"min": 0, "max": 0, "avg": 0, "std": 0}
    
    return {
        "min": min(times),
        "max": max(times),
        "avg": sum(times) / len(times),
        "std": (sum((t - sum(times) / len(times)) ** 2 for t in times) / len(times)) ** 0.5
    }


class LatencyTracker:
    """
    Track latency percentiles for critical operations.
    """
    
    def __init__(self, max_samples: int = 10000):
        """
        Initialize latency tracker.
        
        Args:
            max_samples: Maximum number of samples to keep
        """
        self.max_samples = max_samples
        self.samples: List[float] = []
        self.lock = threading.Lock()
    
    def record(self, latency_ms: float) -> None:
        """
        Record a latency measurement.
        
        Args:
            latency_ms: Latency in milliseconds
        """
        with self.lock:
            self.samples.append(latency_ms)
            if len(self.samples) > self.max_samples:
                self.samples.pop(0)
    
    def get_percentiles(self) -> Dict[str, float]:
        """
        Get latency percentiles.
        
        Returns:
            Dictionary with p50, p90, p95, p99 percentiles
        """
        with self.lock:
            if not self.samples:
                return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}
            
            sorted_samples = sorted(self.samples)
            n = len(sorted_samples)
            
            return {
                "p50": sorted_samples[int(0.5 * n)],
                "p90": sorted_samples[int(0.9 * n)],
                "p95": sorted_samples[int(0.95 * n)],
                "p99": sorted_samples[int(0.99 * n)]
            }
    
    def get_stats(self) -> Dict[str, float]:
        """Get latency statistics."""
        with self.lock:
            if not self.samples:
                return {"min": 0, "max": 0, "avg": 0, "count": 0}
            
            return {
                "min": min(self.samples),
                "max": max(self.samples),
                "avg": sum(self.samples) / len(self.samples),
                "count": len(self.samples)
            }


class ThroughputMonitor:
    """
    Monitor throughput metrics.
    """
    
    def __init__(self, window_seconds: int = 60):
        """
        Initialize throughput monitor.
        
        Args:
            window_seconds: Time window for throughput calculation
        """
        self.window_seconds = window_seconds
        self.events: List[float] = []
        self.lock = threading.Lock()
    
    def record_event(self) -> None:
        """Record an event."""
        with self.lock:
            current_time = time.time()
            self.events.append(current_time)
            
            # Remove old events
            cutoff_time = current_time - self.window_seconds
            self.events = [t for t in self.events if t > cutoff_time]
    
    def get_throughput(self) -> float:
        """
        Get current throughput (events per second).
        
        Returns:
            Throughput in events per second
        """
        with self.lock:
            if not self.events:
                return 0.0
            
            current_time = time.time()
            cutoff_time = current_time - self.window_seconds
            recent_events = [t for t in self.events if t > cutoff_time]
            
            if len(recent_events) < 2:
                return 0.0
            
            time_span = recent_events[-1] - recent_events[0]
            if time_span == 0:
                return 0.0
            
            return (len(recent_events) - 1) / time_span


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return performance_monitor
