#!/usr/bin/env python3
"""
CPU Safety Monitor Module
=========================

Provides real-time CPU monitoring and safety throttling to prevent system overload.
Implements multi-level protection zones to maintain system stability.

Protection Zones:
- Green Zone (0-75%): Normal operation
- Yellow Zone (75-85%): Reduced concurrency + warnings
- Red Zone (85-95%): Queue requests + reject new connections
- Critical Zone (95%+): Emergency mode - reject all new requests

Author: Network Operations Team
Last Updated: July 2025
Auto-deployment Test: v2.0 monitoring files now properly included
"""

import psutil
import threading
import time
import logging
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass
from typing import Optional, Dict, Any
import queue

logger = logging.getLogger(__name__)

@dataclass
class CPUStatus:
    """CPU status information."""
    current_cpu: float
    avg_cpu_1min: float
    avg_cpu_5min: float
    protection_zone: str
    max_concurrent_users: int
    max_workers: int
    requests_queued: int
    requests_rejected: int
    last_updated: datetime

class CPUProtectionZone:
    """CPU protection zone definitions."""
    GREEN = "green"      # 0-75%
    YELLOW = "yellow"    # 75-85%
    RED = "red"          # 85-95%
    CRITICAL = "critical" # 95%+

class CPUSafetyMonitor:
    """
    CPU Safety Monitor for preventing system overload.
    
    Features:
    - Real-time CPU monitoring with configurable intervals
    - Multi-level protection zones with different throttling strategies
    - Request queuing during high CPU periods
    - Automatic recovery when CPU levels normalize
    - Detailed logging and metrics collection
    """
    
    def __init__(self, 
                 green_threshold: float = 75.0,
                 yellow_threshold: float = 85.0,
                 red_threshold: float = 95.0,
                 monitoring_interval: float = 1.0,
                 history_window: int = 300):  # 5 minutes
        """
        Initialize CPU Safety Monitor.
        
        Args:
            green_threshold: CPU% threshold for yellow zone (default: 75%)
            yellow_threshold: CPU% threshold for red zone (default: 85%)
            red_threshold: CPU% threshold for critical zone (default: 95%)
            monitoring_interval: CPU check interval in seconds (default: 1.0)
            history_window: Number of historical readings to keep (default: 300)
        """
        self.green_threshold = green_threshold
        self.yellow_threshold = yellow_threshold
        self.red_threshold = red_threshold
        self.monitoring_interval = monitoring_interval
        
        # CPU history for averaging
        self.cpu_history = deque(maxlen=history_window)
        self.cpu_lock = threading.Lock()
        
        # Current status
        self.current_status = CPUStatus(
            current_cpu=0.0,
            avg_cpu_1min=0.0,
            avg_cpu_5min=0.0,
            protection_zone=CPUProtectionZone.GREEN,
            max_concurrent_users=10,
            max_workers=8,
            requests_queued=0,
            requests_rejected=0,
            last_updated=datetime.now()
        )
        
        # Request queue for throttling
        self.request_queue = queue.Queue(maxsize=50)  # Max 50 queued requests
        self.queue_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'requests_queued': 0,
            'requests_rejected': 0,
            'zone_changes': 0,
            'last_zone_change': None
        }
        
        # Monitoring thread
        self.monitoring_active = False
        self.monitor_thread = None
        
        logger.info(f"CPU Safety Monitor initialized - Thresholds: Green<{green_threshold}%, Yellow<{yellow_threshold}%, Red<{red_threshold}%")
    
    def start_monitoring(self):
        """Start CPU monitoring thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("CPU Safety Monitor started")
    
    def stop_monitoring(self):
        """Stop CPU monitoring thread."""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        logger.info("CPU Safety Monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._update_cpu_status()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"CPU monitoring error: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def _update_cpu_status(self):
        """Update current CPU status and protection zone."""
        try:
            # Get current CPU usage
            current_cpu = psutil.cpu_percent(interval=None)
            
            with self.cpu_lock:
                # Add to history
                self.cpu_history.append({
                    'cpu': current_cpu,
                    'timestamp': datetime.now()
                })
                
                # Calculate averages
                if len(self.cpu_history) > 0:
                    recent_readings = [r['cpu'] for r in list(self.cpu_history)[-60:]]  # Last 60 seconds
                    avg_1min = sum(recent_readings) / len(recent_readings)
                    
                    all_readings = [r['cpu'] for r in self.cpu_history]
                    avg_5min = sum(all_readings) / len(all_readings)
                else:
                    avg_1min = current_cpu
                    avg_5min = current_cpu
                
                # Determine protection zone
                old_zone = self.current_status.protection_zone
                new_zone = self._determine_protection_zone(avg_1min)
                
                # Update concurrent limits based on zone
                max_users, max_workers = self._get_zone_limits(new_zone)
                
                # Update status
                self.current_status = CPUStatus(
                    current_cpu=current_cpu,
                    avg_cpu_1min=avg_1min,
                    avg_cpu_5min=avg_5min,
                    protection_zone=new_zone,
                    max_concurrent_users=max_users,
                    max_workers=max_workers,
                    requests_queued=self.request_queue.qsize(),
                    requests_rejected=self.stats['requests_rejected'],
                    last_updated=datetime.now()
                )
                
                # Log zone changes
                if old_zone != new_zone:
                    self.stats['zone_changes'] += 1
                    self.stats['last_zone_change'] = datetime.now()
                    logger.warning(f"CPU Protection Zone changed: {old_zone} -> {new_zone} "
                                 f"(CPU: {current_cpu:.1f}%, 1min avg: {avg_1min:.1f}%)")
        
        except Exception as e:
            logger.error(f"Error updating CPU status: {e}")
    
    def _determine_protection_zone(self, avg_cpu: float) -> str:
        """Determine protection zone based on average CPU."""
        if avg_cpu >= self.red_threshold:
            return CPUProtectionZone.CRITICAL
        elif avg_cpu >= self.yellow_threshold:
            return CPUProtectionZone.RED
        elif avg_cpu >= self.green_threshold:
            return CPUProtectionZone.YELLOW
        else:
            return CPUProtectionZone.GREEN
    
    def _get_zone_limits(self, zone: str) -> tuple:
        """Get concurrent user and worker limits for protection zone."""
        zone_config = {
            CPUProtectionZone.GREEN: (10, 8),     # Normal limits
            CPUProtectionZone.YELLOW: (6, 4),    # Reduced limits
            CPUProtectionZone.RED: (3, 2),       # Minimal limits
            CPUProtectionZone.CRITICAL: (1, 1)   # Emergency limits
        }
        return zone_config.get(zone, (1, 1))
    
    def can_accept_request(self):
        """
        Check if system can accept a new request.
        
        Returns:
            tuple: (can_accept: bool, reason: str)
        """
        status = self.get_status()
        
        if status.protection_zone == CPUProtectionZone.CRITICAL:
            self.stats['requests_rejected'] += 1
            return False, f"System overloaded (CPU: {status.current_cpu:.1f}%). Please try again later."
        
        if status.protection_zone == CPUProtectionZone.RED:
            if self.request_queue.full():
                self.stats['requests_rejected'] += 1
                return False, f"System busy (CPU: {status.current_cpu:.1f}%). Request queue full."
            else:
                return True, "Request queued due to high CPU usage"
        
        return True, "OK"
    
    def get_status(self) -> CPUStatus:
        """Get current CPU status."""
        with self.cpu_lock:
            return self.current_status
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        status = self.get_status()
        return {
            'current_status': {
                'cpu_current': status.current_cpu,
                'cpu_avg_1min': status.avg_cpu_1min,
                'cpu_avg_5min': status.avg_cpu_5min,
                'protection_zone': status.protection_zone,
                'max_concurrent_users': status.max_concurrent_users,
                'max_workers': status.max_workers,
                'requests_queued': status.requests_queued,
                'last_updated': status.last_updated.isoformat()
            },
            'statistics': self.stats.copy(),
            'thresholds': {
                'green_threshold': self.green_threshold,
                'yellow_threshold': self.yellow_threshold,
                'red_threshold': self.red_threshold
            }
        }
    
    def reset_statistics(self):
        """Reset monitoring statistics."""
        self.stats = {
            'total_requests': 0,
            'requests_queued': 0,
            'requests_rejected': 0,
            'zone_changes': 0,
            'last_zone_change': None
        }
        logger.info("CPU Safety Monitor statistics reset")

# Global CPU monitor instance
cpu_monitor = None

def initialize_cpu_monitor(**kwargs) -> CPUSafetyMonitor:
    """Initialize global CPU monitor instance."""
    global cpu_monitor
    if cpu_monitor is None:
        cpu_monitor = CPUSafetyMonitor(**kwargs)
        cpu_monitor.start_monitoring()
    return cpu_monitor

def get_cpu_monitor() -> Optional[CPUSafetyMonitor]:
    """Get global CPU monitor instance."""
    return cpu_monitor

def shutdown_cpu_monitor():
    """Shutdown global CPU monitor instance."""
    global cpu_monitor
    if cpu_monitor:
        cpu_monitor.stop_monitoring()
        cpu_monitor = None
