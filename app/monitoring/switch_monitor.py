#!/usr/bin/env python3
"""
Dell Switch Protection Monitor
=======================================

This module provides comprehensive protection for Dell switches against:
- Too many concurrent SSH connections
- Command flooding/rate limiting
- Switch-specific connection throttling
- Connection health monitoring
- Automatic backoff and retry logic

🛡️ SWITCH PROTECTION FEATURES:
- Per-switch concurrent connection limits (max 8 per switch)
- Global switch pool connection limits (max 64 total)
- Command rate limiting (max 10 commands/second per switch)  
- Connection health monitoring and automatic recovery
- Exponential backoff for failed connections
- Switch load balancing and priority queuing

🔧 DELL SWITCH LIMITS (typical):
- N2000/N3000 series: 10-16 concurrent SSH sessions max
- Command processing: ~20-50 commands/second max
- Memory constraints under heavy load
- CPU usage spikes during MAC table operations

Repository: https://github.com/Crispy-Pasta/DellPortTracer
Version: 1.0.0
Author: Network Operations Team
"""

import threading
import time
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
import queue

logger = logging.getLogger(__name__)

class SwitchProtectionMonitor:
    """
    Monitors and protects Dell switches from connection overload.
    
    Features:
    - Per-switch connection limits
    - Global connection pool management
    - Command rate limiting per switch
    - Connection health tracking
    - Automatic backoff for overloaded switches
    """
    
    def __init__(self, 
                 max_connections_per_switch=8,    # Dell switches: ~10 max SSH sessions 
                 max_total_connections=64,        # Global limit across all switches
                 commands_per_second_limit=10,    # Commands per second per switch
                 connection_timeout=30,           # Connection timeout seconds
                 backoff_initial_delay=5,         # Initial backoff delay
                 backoff_max_delay=300):          # Maximum backoff delay (5 minutes)
        
        self.max_connections_per_switch = max_connections_per_switch
        self.max_total_connections = max_total_connections
        self.commands_per_second_limit = commands_per_second_limit
        self.connection_timeout = connection_timeout
        self.backoff_initial_delay = backoff_initial_delay
        self.backoff_max_delay = backoff_max_delay
        
        # Per-switch tracking
        self.switch_connections = defaultdict(lambda: {
            'active_count': 0,
            'queue_count': 0,
            'last_commands': deque(maxlen=100),  # Track command timestamps
            'health_status': 'healthy',           # healthy, degraded, overloaded
            'last_failure': None,
            'backoff_delay': 0,
            'total_commands': 0,
            'failed_commands': 0,
            'lock': threading.Lock()
        })
        
        # Global tracking
        self.total_active_connections = 0
        self.connection_queue = queue.Queue()
        self.global_lock = threading.Lock()
        
        # Health monitoring
        self.monitor_thread = None
        self.monitor_running = False
        
        logger.info(f"Switch Protection Monitor initialized - Max per switch: {max_connections_per_switch}, Global max: {max_total_connections}")
    
    def start_monitoring(self):
        """Start the background health monitoring thread."""
        if not self.monitor_running:
            self.monitor_running = True
            self.monitor_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Switch protection monitoring started")
    
    def stop_monitoring(self):
        """Stop the background monitoring thread."""
        self.monitor_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Switch protection monitoring stopped")
    
    def _health_monitor_loop(self):
        """Background thread that monitors switch health and adjusts protection levels."""
        while self.monitor_running:
            try:
                current_time = datetime.now()
                
                for switch_ip, switch_data in self.switch_connections.items():
                    with switch_data['lock']:
                        # Check command rate in last minute
                        one_minute_ago = current_time - timedelta(minutes=1)
                        recent_commands = [cmd_time for cmd_time in switch_data['last_commands'] 
                                         if cmd_time > one_minute_ago]
                        
                        commands_per_minute = len(recent_commands)
                        
                        # Update health status based on metrics
                        if commands_per_minute > (self.commands_per_second_limit * 40):  # 40 seconds worth
                            switch_data['health_status'] = 'overloaded'
                            switch_data['backoff_delay'] = min(switch_data['backoff_delay'] * 2 or self.backoff_initial_delay, 
                                                             self.backoff_max_delay)
                            logger.warning(f"Switch {switch_ip} marked as OVERLOADED - {commands_per_minute} commands/min")
                        
                        elif commands_per_minute > (self.commands_per_second_limit * 20):  # 20 seconds worth
                            switch_data['health_status'] = 'degraded'
                            logger.info(f"Switch {switch_ip} marked as DEGRADED - {commands_per_minute} commands/min")
                        
                        else:
                            if switch_data['health_status'] != 'healthy':
                                logger.info(f"Switch {switch_ip} recovered to HEALTHY status")
                            switch_data['health_status'] = 'healthy'
                            switch_data['backoff_delay'] = max(switch_data['backoff_delay'] * 0.5, 0)
                
                # Log global statistics every 5 minutes
                if int(current_time.timestamp()) % 300 == 0:
                    self._log_protection_stats()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in switch protection health monitor: {str(e)}")
                time.sleep(30)  # Longer sleep on error
    
    def can_connect_to_switch(self, switch_ip):
        """
        Check if a new connection to the switch is allowed.
        
        Returns:
            tuple: (allowed: bool, reason: str, wait_time: float)
        """
        switch_data = self.switch_connections[switch_ip]
        
        with switch_data['lock']:
            # Check switch health status
            if switch_data['health_status'] == 'overloaded':
                if switch_data['backoff_delay'] > 0:
                    return False, f"Switch overloaded, backoff active ({switch_data['backoff_delay']:.1f}s remaining)", switch_data['backoff_delay']
            
            # Check per-switch connection limit
            if switch_data['active_count'] >= self.max_connections_per_switch:
                return False, f"Switch connection limit reached ({self.max_connections_per_switch})", 5.0
            
            # Check global connection limit
            with self.global_lock:
                if self.total_active_connections >= self.max_total_connections:
                    return False, f"Global connection limit reached ({self.max_total_connections})", 10.0
            
            # Check command rate limiting
            current_time = datetime.now()
            one_second_ago = current_time - timedelta(seconds=1)
            recent_commands = [cmd_time for cmd_time in switch_data['last_commands'] 
                             if cmd_time > one_second_ago]
            
            if len(recent_commands) >= self.commands_per_second_limit:
                return False, f"Command rate limit reached ({self.commands_per_second_limit}/sec)", 1.0
        
        return True, "Connection allowed", 0.0
    
    def acquire_switch_connection(self, switch_ip, username="system"):
        """
        Acquire a connection slot for a switch.
        
        Returns:
            bool: True if connection acquired, False if rejected
        """
        allowed, reason, wait_time = self.can_connect_to_switch(switch_ip)
        
        if not allowed:
            logger.warning(f"Connection to {switch_ip} REJECTED for {username}: {reason}")
            return False
        
        switch_data = self.switch_connections[switch_ip]
        
        with switch_data['lock']:
            switch_data['active_count'] += 1
            
        with self.global_lock:
            self.total_active_connections += 1
        
        logger.info(f"Connection to {switch_ip} ACQUIRED for {username} ({switch_data['active_count']}/{self.max_connections_per_switch} switch, {self.total_active_connections}/{self.max_total_connections} global)")
        return True
    
    def release_switch_connection(self, switch_ip, username="system"):
        """Release a connection slot for a switch."""
        switch_data = self.switch_connections[switch_ip]
        
        with switch_data['lock']:
            if switch_data['active_count'] > 0:
                switch_data['active_count'] -= 1
        
        with self.global_lock:
            if self.total_active_connections > 0:
                self.total_active_connections -= 1
        
        logger.info(f"Connection to {switch_ip} RELEASED for {username} ({switch_data['active_count']}/{self.max_connections_per_switch} switch, {self.total_active_connections}/{self.max_total_connections} global)")
    
    def record_command_execution(self, switch_ip, success=True):
        """Record a command execution for rate limiting and health monitoring."""
        switch_data = self.switch_connections[switch_ip]
        current_time = datetime.now()
        
        with switch_data['lock']:
            switch_data['last_commands'].append(current_time)
            switch_data['total_commands'] += 1
            
            if not success:
                switch_data['failed_commands'] += 1
                switch_data['last_failure'] = current_time
                
                # Increase backoff delay on failures
                if switch_data['failed_commands'] > 3:
                    switch_data['backoff_delay'] = min(switch_data['backoff_delay'] + 5, self.backoff_max_delay)
    
    def get_switch_stats(self, switch_ip):
        """Get statistics for a specific switch."""
        switch_data = self.switch_connections[switch_ip]
        
        with switch_data['lock']:
            current_time = datetime.now()
            one_minute_ago = current_time - timedelta(minutes=1)
            recent_commands = [cmd_time for cmd_time in switch_data['last_commands'] 
                             if cmd_time > one_minute_ago]
            
            return {
                'switch_ip': switch_ip,
                'active_connections': switch_data['active_count'],
                'max_connections': self.max_connections_per_switch,
                'health_status': switch_data['health_status'],
                'commands_last_minute': len(recent_commands),
                'total_commands': switch_data['total_commands'],
                'failed_commands': switch_data['failed_commands'],
                'backoff_delay': switch_data['backoff_delay'],
                'last_failure': switch_data['last_failure'].isoformat() if switch_data['last_failure'] else None
            }
    
    def get_global_stats(self):
        """Get global protection statistics."""
        with self.global_lock:
            switch_count = len([ip for ip, data in self.switch_connections.items() 
                              if data['active_count'] > 0])
            
            return {
                'total_active_connections': self.total_active_connections,
                'max_total_connections': self.max_total_connections,
                'active_switches': switch_count,
                'total_switches_seen': len(self.switch_connections),
                'overloaded_switches': len([ip for ip, data in self.switch_connections.items() 
                                          if data['health_status'] == 'overloaded']),
                'degraded_switches': len([ip for ip, data in self.switch_connections.items() 
                                        if data['health_status'] == 'degraded'])
            }
    
    def _log_protection_stats(self):
        """Log comprehensive protection statistics."""
        global_stats = self.get_global_stats()
        
        logger.info(f"Switch Protection Stats - Active: {global_stats['total_active_connections']}/{global_stats['max_total_connections']}, "
                   f"Switches: {global_stats['active_switches']} active, "
                   f"Health: {global_stats['overloaded_switches']} overloaded, {global_stats['degraded_switches']} degraded")
        
        # Log individual switch stats for overloaded switches
        for switch_ip, switch_data in self.switch_connections.items():
            if switch_data['health_status'] in ['overloaded', 'degraded']:
                stats = self.get_switch_stats(switch_ip)
                logger.warning(f"Switch {switch_ip} - Status: {stats['health_status']}, "
                             f"Connections: {stats['active_connections']}/{stats['max_connections']}, "
                             f"Commands/min: {stats['commands_last_minute']}, "
                             f"Failed: {stats['failed_commands']}")


# Global switch protection monitor instance
_switch_monitor = None
_monitor_lock = threading.Lock()

def initialize_switch_protection_monitor(**kwargs):
    """Initialize the global switch protection monitor."""
    global _switch_monitor
    
    with _monitor_lock:
        if _switch_monitor is None:
            _switch_monitor = SwitchProtectionMonitor(**kwargs)
            _switch_monitor.start_monitoring()
            logger.info("Global switch protection monitor initialized")
    
    return _switch_monitor

def get_switch_protection_monitor():
    """Get the global switch protection monitor instance."""
    if _switch_monitor is None:
        raise RuntimeError("Switch protection monitor not initialized. Call initialize_switch_protection_monitor() first.")
    return _switch_monitor
