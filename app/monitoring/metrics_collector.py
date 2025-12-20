"""
Metrics Collector Module

This module provides a central collection point for various system metrics,
integrating CPU, memory, network, and thread monitoring into a single interface.
"""
from app.monitoring.cpu_monitor import CPUMonitor
from app.monitoring.network_monitor import NetworkMonitor
from app.monitoring.thread_monitor import ThreadMonitor
import psutil
import threading
import time
from typing import Dict, Any, Optional, List
from app.logging_config import logger

class MetricsCollector:
    """
    Collects and aggregates system metrics from various monitors.
    
    This class serves as a facade for the individual monitoring components,
    providing a single point of access for all system metrics.
    
    Attributes:
        _cpu_monitor (CPUMonitor): Monitor for CPU metrics
        _network_monitor (NetworkMonitor): Monitor for network metrics
        _thread_monitor (ThreadMonitor): Monitor for thread metrics
        _interval (int): Metrics collection interval in seconds
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'MetricsCollector':
        """
        Get or create the singleton instance of MetricsCollector.
        
        Returns:
            MetricsCollector: The singleton instance
        """
        if cls._instance is None:
            cls._instance = MetricsCollector()
        return cls._instance
    
    def __init__(self, interval: int = 5):
        """
        Initialize the metrics collector with individual monitors.
        
        Args:
            interval (int): Metrics collection interval in seconds
        """
        self._cpu_monitor = CPUMonitor(interval=interval)
        self._network_monitor = NetworkMonitor(interval=interval)
        self._thread_monitor = ThreadMonitor(interval=interval)
        self._interval = interval
        self._is_running = False
    
    def start(self) -> None:
        """
        Start all monitoring components.
        """
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start individual monitors
        self._cpu_monitor.start()
        self._network_monitor.start()
        self._thread_monitor.start()
        
        logger.info("Started all monitoring components")
    
    def stop(self) -> None:
        """
        Stop all monitoring components.
        """
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Stop individual monitors
        self._cpu_monitor.stop()
        self._network_monitor.stop()
        self._thread_monitor.stop()
        
        logger.info("Stopped all monitoring components")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get a comprehensive system status report.
        
        Returns:
            Dict[str, Any]: Dictionary with various system metrics
        """
        # Get memory info
        try:
            memory = psutil.virtual_memory()
            memory_info = {
                "total_memory": memory.total,
                "available_memory": memory.available,
                "used_memory": memory.used,
                "memory_percent": memory.percent
            }
        except Exception as e:
            logger.error(f"Error getting memory info: {str(e)}")
            memory_info = {
                "total_memory": 0,
                "available_memory": 0,
                "used_memory": 0,
                "memory_percent": 0
            }
        
        # Collect metrics from all monitors
        return {
            "timestamp": time.time(),
            "cpu": self._cpu_monitor.get_current_usage(),
            "memory": memory_info,
            "network": self._network_monitor.get_current_rates(),
            "threads": self._thread_monitor.get_current_thread_count()
        }
    
    def get_historical_metrics(self, duration: Optional[int] = None) -> Dict[str, Any]:
        """
        Get historical metrics data.
        
        Args:
            duration (int, optional): Time period in seconds, or None for all history
            
        Returns:
            Dict[str, Any]: Dictionary with historical metrics from all monitors
        """
        return {
            "cpu_history": self._cpu_monitor.get_history(),
            "network_history": self._network_monitor.get_history(),
            "thread_history": self._thread_monitor.get_history()
        }
    
    def get_performance_summary(self, duration: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a summary of performance metrics.
        
        Args:
            duration (int, optional): Time period in seconds, or None for all history
            
        Returns:
            Dict[str, Any]: Dictionary with performance summary data
        """
        cpu_avg = self._cpu_monitor.get_average_usage(duration)
        network_avg = self._network_monitor.get_average_rates(duration)
        thread_avg = self._thread_monitor.get_average_count(duration)
        
        return {
            "cpu_average": cpu_avg,
            "network_average": network_avg,
            "thread_average": thread_avg
        }
    
    def get_cpu_monitor(self) -> CPUMonitor:
        """Get the CPU monitor instance."""
        return self._cpu_monitor
    
    def get_network_monitor(self) -> NetworkMonitor:
        """Get the network monitor instance."""
        return self._network_monitor
    
    def get_thread_monitor(self) -> ThreadMonitor:
        """Get the thread monitor instance."""
        return self._thread_monitor
    
    @property
    def is_running(self) -> bool:
        """
        Check if all monitoring components are running.
        
        Returns:
            bool: True if all monitoring is active, False otherwise
        """
        return (
            self._is_running and 
            self._cpu_monitor.is_running and
            self._network_monitor.is_running and
            self._thread_monitor.is_running
        )
