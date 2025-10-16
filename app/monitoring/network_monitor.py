"""
Network Monitor Module

This module provides utilities for monitoring network activity by the application.
"""
import psutil
import time
import threading
from typing import Dict, Any, Optional, Tuple
from app.logging_config import logger

class NetworkMonitor:
    """
    Monitors network activity of the system.
    
    This class runs a background thread to collect network usage statistics at
    regular intervals and provides methods to retrieve current and historical
    network activity data.
    
    Attributes:
        interval (int): Sampling interval in seconds
        history_size (int): Maximum number of history samples to keep
        running (bool): Whether monitoring thread is running
        _network_history (list): History of network usage readings
    """
    
    def __init__(self, interval: int = 5, history_size: int = 60):
        """
        Initialize the network monitor with specified settings.
        
        Args:
            interval (int): Sampling interval in seconds
            history_size (int): Maximum number of history samples to keep
        """
        self.interval = interval
        self.history_size = history_size
        self.running = False
        self._network_history = []
        self._last_io_counters = None
        self._thread = None
    
    def start(self) -> None:
        """
        Start the network monitoring thread.
        """
        if self.running:
            return
        
        self.running = True
        self._last_io_counters = psutil.net_io_counters()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Network monitoring started with {self.interval}s interval")
    
    def stop(self) -> None:
        """
        Stop the network monitoring thread.
        """
        self.running = False
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
            logger.info("Network monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """
        Main monitoring loop that collects network usage data at regular intervals.
        """
        while self.running:
            try:
                # Get current network counters
                current_time = time.time()
                current_counters = psutil.net_io_counters()
                
                if self._last_io_counters:
                    # Calculate rates
                    sent_bytes = current_counters.bytes_sent - self._last_io_counters.bytes_sent
                    recv_bytes = current_counters.bytes_recv - self._last_io_counters.bytes_recv
                    
                    # Calculate bytes per second
                    sent_rate = sent_bytes / self.interval
                    recv_rate = recv_bytes / self.interval
                    
                    # Store data point
                    data_point = {
                        "timestamp": current_time,
                        "sent_bytes": sent_bytes,
                        "recv_bytes": recv_bytes,
                        "sent_rate": sent_rate,
                        "recv_rate": recv_rate
                    }
                    
                    self._network_history.append(data_point)
                    
                    # Trim history if needed
                    if len(self._network_history) > self.history_size:
                        self._network_history = self._network_history[-self.history_size:]
                
                # Update last counters
                self._last_io_counters = current_counters
                
            except Exception as e:
                logger.error(f"Error in network monitoring: {str(e)}")
            
            # Wait for next interval
            time.sleep(self.interval)
    
    def get_current_rates(self) -> Dict[str, float]:
        """
        Get current network transfer rates.
        
        Returns:
            Dict[str, float]: Dictionary with sent and received rates in bytes/second
        """
        try:
            # Take two measurements to calculate rate
            counters1 = psutil.net_io_counters()
            time.sleep(1.0)  # Sample over 1 second
            counters2 = psutil.net_io_counters()
            
            sent_rate = counters2.bytes_sent - counters1.bytes_sent
            recv_rate = counters2.bytes_recv - counters1.bytes_recv
            
            return {
                "sent_rate": sent_rate,  # bytes per second
                "recv_rate": recv_rate   # bytes per second
            }
        except Exception as e:
            logger.error(f"Error getting current network rates: {str(e)}")
            return {"sent_rate": 0.0, "recv_rate": 0.0}
    
    def get_history(self) -> list:
        """
        Get network usage history.
        
        Returns:
            list: List of network usage data points
        """
        return self._network_history
    
    def get_total_transfer(self) -> Dict[str, int]:
        """
        Get total network transfer amounts.
        
        Returns:
            Dict[str, int]: Dictionary with total bytes sent and received
        """
        try:
            counters = psutil.net_io_counters()
            return {
                "total_sent": counters.bytes_sent,
                "total_recv": counters.bytes_recv
            }
        except Exception as e:
            logger.error(f"Error getting total network transfer: {str(e)}")
            return {"total_sent": 0, "total_recv": 0}
    
    def get_average_rates(self, seconds: Optional[int] = None) -> Dict[str, float]:
        """
        Calculate average network rates over a period of time.
        
        Args:
            seconds (int, optional): Time period in seconds, or None for all history
            
        Returns:
            Dict[str, float]: Dictionary with average sent and receive rates
        """
        if not self._network_history:
            return {"avg_sent_rate": 0.0, "avg_recv_rate": 0.0}
        
        # If seconds specified, filter history by time
        history = self._network_history
        if seconds is not None:
            cutoff_time = time.time() - seconds
            history = [point for point in history if point["timestamp"] >= cutoff_time]
        
        if not history:
            return {"avg_sent_rate": 0.0, "avg_recv_rate": 0.0}
        
        # Calculate averages
        avg_sent = sum(point["sent_rate"] for point in history) / len(history)
        avg_recv = sum(point["recv_rate"] for point in history) / len(history)
        
        return {
            "avg_sent_rate": avg_sent,
            "avg_recv_rate": avg_recv
        }
    
    def format_bytes(self, bytes_value: int) -> str:
        """
        Format bytes value as human-readable string.
        
        Args:
            bytes_value (int): Bytes to format
            
        Returns:
            str: Formatted string (e.g., "1.23 MB")
        """
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        index = 0
        
        while bytes_value >= 1024 and index < len(suffixes) - 1:
            bytes_value /= 1024.0
            index += 1
        
        return f"{bytes_value:.2f} {suffixes[index]}"
    
    @property
    def is_running(self) -> bool:
        """
        Check if monitoring thread is running.
        
        Returns:
            bool: True if monitoring is active, False otherwise
        """
        return self.running and (self._thread is not None) and self._thread.is_alive()
