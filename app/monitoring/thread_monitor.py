"""
Thread Monitor Module

This module provides utilities for monitoring threads and their activity.
"""
import threading
import time
import psutil
from typing import Dict, Any, Optional, List
from app.logging_config import logger

class ThreadMonitor:
    """
    Monitors application thread activity and statistics.
    
    This class collects information about active threads, their states,
    and resource usage to help identify potential threading issues and
    performance bottlenecks.
    
    Attributes:
        interval (int): Sampling interval in seconds
        history_size (int): Maximum number of history samples to keep
        running (bool): Whether monitoring thread is running
        _history (list): Historical thread data
        _thread (threading.Thread): Monitoring thread
    """
    
    def __init__(self, interval: int = 5, history_size: int = 60):
        """
        Initialize the thread monitor with specified settings.
        
        Args:
            interval (int): Sampling interval in seconds
            history_size (int): Maximum number of history samples to keep
        """
        self.interval = interval
        self.history_size = history_size
        self.running = False
        self._history = []
        self._thread = None
    
    def start(self) -> None:
        """
        Start the thread monitoring process.
        """
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Thread monitoring started with {self.interval}s interval")
    
    def stop(self) -> None:
        """
        Stop the thread monitoring process.
        """
        self.running = False
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
            logger.info("Thread monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """
        Main monitoring loop that collects thread data at regular intervals.
        """
        while self.running:
            try:
                # Collect thread data
                timestamp = time.time()
                thread_count = threading.active_count()
                threads_info = self._get_threads_info()
                
                # Store data point
                data_point = {
                    "timestamp": timestamp,
                    "thread_count": thread_count,
                    "threads_info": threads_info
                }
                
                self._history.append(data_point)
                
                # Trim history if needed
                if len(self._history) > self.history_size:
                    self._history = self._history[-self.history_size:]
                
            except Exception as e:
                logger.error(f"Error in thread monitoring: {str(e)}")
            
            # Wait for next interval
            time.sleep(self.interval)
    
    def _get_threads_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all active threads.
        
        Returns:
            List[Dict[str, Any]]: List of thread information dictionaries
        """
        result = []
        
        for thread in threading.enumerate():
            try:
                thread_info = {
                    "name": thread.name,
                    "ident": thread.ident,
                    "alive": thread.is_alive(),
                    "daemon": thread.daemon
                }
                result.append(thread_info)
            except Exception:
                pass
        
        return result
    
    def get_current_thread_count(self) -> Dict[str, int]:
        """
        Get current thread count.
        
        Returns:
            Dict[str, int]: Dictionary with thread count and daemon thread count
        """
        threads = threading.enumerate()
        daemon_count = sum(1 for thread in threads if thread.daemon)
        non_daemon_count = len(threads) - daemon_count
        
        return {
            "total_threads": len(threads),
            "daemon_threads": daemon_count,
            "non_daemon_threads": non_daemon_count
        }
    
    def get_history(self) -> list:
        """
        Get thread history data.
        
        Returns:
            list: Historical thread data
        """
        return self._history
    
    def get_average_count(self, seconds: Optional[int] = None) -> Dict[str, float]:
        """
        Calculate average thread count over a period of time.
        
        Args:
            seconds (int, optional): Time period in seconds, or None for all history
            
        Returns:
            Dict[str, float]: Dictionary with average thread counts
        """
        if not self._history:
            return {"avg_thread_count": 0.0}
        
        # If seconds specified, filter history by time
        history = self._history
        if seconds is not None:
            cutoff_time = time.time() - seconds
            history = [point for point in history if point["timestamp"] >= cutoff_time]
        
        if not history:
            return {"avg_thread_count": 0.0}
        
        # Calculate average
        avg_count = sum(point["thread_count"] for point in history) / len(history)
        
        return {"avg_thread_count": avg_count}
    
    def get_thread_by_name(self, name: str) -> Optional[threading.Thread]:
        """
        Find a thread by name.
        
        Args:
            name (str): Name of the thread to find
            
        Returns:
            Optional[threading.Thread]: The found thread or None
        """
        for thread in threading.enumerate():
            if thread.name == name:
                return thread
        return None
    
    @property
    def is_running(self) -> bool:
        """
        Check if monitoring thread is running.
        
        Returns:
            bool: True if monitoring is active, False otherwise
        """
        return self.running and (self._thread is not None) and self._thread.is_alive()
