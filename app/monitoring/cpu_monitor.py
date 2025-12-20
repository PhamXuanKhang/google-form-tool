"""
CPU Monitor Module

This module provides utilities for monitoring CPU usage by the application.
"""
import psutil
import time
import threading
from typing import Dict, Any, Optional
from app.logging_config import logger

class CPUMonitor:
    """
    Monitors CPU usage by the application process and overall system.
    
    This class runs a background thread to collect CPU usage statistics at
    regular intervals and provides methods to retrieve current and historical
    usage data.
    
    Attributes:
        interval (int): Sampling interval in seconds
        history_size (int): Maximum number of history samples to keep
        running (bool): Whether monitoring thread is running
        _process (Process): Current process object
        _cpu_history (list): History of CPU usage readings
    """
    
    def __init__(self, interval: int = 5, history_size: int = 60):
        """
        Initialize the CPU monitor with specified settings.
        
        Args:
            interval (int): Sampling interval in seconds
            history_size (int): Maximum number of history samples to keep
        """
        self.interval = interval
        self.history_size = history_size
        self.running = False
        self._process = psutil.Process()
        self._cpu_history = []
        self._thread = None
    
    def start(self) -> None:
        """
        Start the CPU monitoring thread.
        """
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"CPU monitoring started with {self.interval}s interval")
    
    def stop(self) -> None:
        """
        Stop the CPU monitoring thread.
        """
        self.running = False
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
            logger.info("CPU monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """
        Main monitoring loop that collects CPU usage data at regular intervals.
        """
        while self.running:
            try:
                # Collect CPU usage data
                timestamp = time.time()
                process_cpu = self._process.cpu_percent()
                system_cpu = psutil.cpu_percent()
                
                # Store data point
                data_point = {
                    "timestamp": timestamp,
                    "process_cpu": process_cpu,
                    "system_cpu": system_cpu
                }
                
                self._cpu_history.append(data_point)
                
                # Trim history if needed
                if len(self._cpu_history) > self.history_size:
                    self._cpu_history = self._cpu_history[-self.history_size:]
                
            except Exception as e:
                logger.error(f"Error in CPU monitoring: {str(e)}")
            
            # Wait for next interval
            time.sleep(self.interval)
    
    def get_current_usage(self) -> Dict[str, float]:
        """
        Get current CPU usage for process and system.
        
        Returns:
            Dict[str, float]: Dictionary with process and system CPU percentages
        """
        try:
            return {
                "process_cpu": self._process.cpu_percent(),
                "system_cpu": psutil.cpu_percent()
            }
        except Exception as e:
            logger.error(f"Error getting current CPU usage: {str(e)}")
            return {"process_cpu": 0.0, "system_cpu": 0.0}
    
    def get_history(self) -> list:
        """
        Get CPU usage history.
        
        Returns:
            list: List of CPU usage data points
        """
        return self._cpu_history
    
    def get_average_usage(self, seconds: Optional[int] = None) -> Dict[str, float]:
        """
        Calculate average CPU usage over a period of time.
        
        Args:
            seconds (int, optional): Time period in seconds, or None for all history
            
        Returns:
            Dict[str, float]: Dictionary with average process and system CPU percentages
        """
        if not self._cpu_history:
            return {"process_cpu_avg": 0.0, "system_cpu_avg": 0.0}
        
        # If seconds specified, filter history by time
        history = self._cpu_history
        if seconds is not None:
            cutoff_time = time.time() - seconds
            history = [point for point in history if point["timestamp"] >= cutoff_time]
        
        if not history:
            return {"process_cpu_avg": 0.0, "system_cpu_avg": 0.0}
        
        # Calculate averages
        process_avg = sum(point["process_cpu"] for point in history) / len(history)
        system_avg = sum(point["system_cpu"] for point in history) / len(history)
        
        return {
            "process_cpu_avg": process_avg,
            "system_cpu_avg": system_avg
        }
    
    @property
    def is_running(self) -> bool:
        """
        Check if monitoring thread is running.
        
        Returns:
            bool: True if monitoring is active, False otherwise
        """
        return self.running and (self._thread is not None) and self._thread.is_alive()
