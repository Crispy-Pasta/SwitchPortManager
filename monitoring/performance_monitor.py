#!/usr/bin/env python3
"""
Dell Switch Port Tracer - Performance Monitor
============================================

Advanced performance monitoring system for Dell Port Tracer with:
- Real-time CPU, memory, and network monitoring
- Database performance metrics
- Switch connection health tracking
- Automated alerting and reporting
- Prometheus metrics export
- Grafana dashboard integration

Version: 2.1.3
Updated: August 2025
"""

import os
import sys
import time
import json
import psutil
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque, defaultdict

# Optional integrations
try:
    import prometheus_client
    from prometheus_client import Counter, Histogram, Gauge, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

@dataclass
class SystemMetrics:
    """System performance metrics snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_used_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    load_average: Tuple[float, float, float]

@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    timestamp: datetime
    active_users: int
    concurrent_traces: int
    database_connections: int
    switch_connections: int
    api_requests_per_minute: int
    vlan_operations_per_minute: int
    error_rate_percent: float
    avg_response_time_ms: float

@dataclass
class PerformanceAlert:
    """Performance alert definition."""
    timestamp: datetime
    alert_type: str
    severity: str  # 'info', 'warning', 'critical'
    message: str
    metric_name: str
    current_value: float
    threshold: float
    resolved: bool = False

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for Dell Port Tracer.
    
    Features:
    - Real-time system metrics collection
    - Application performance tracking
    - Automated alerting system
    - Prometheus metrics export
    - Historical data analysis
    - Performance recommendations
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_default_config()
        self.logger = self._setup_logging()
        self.running = False
        self.monitor_thread = None
        
        # Metrics storage
        self.system_metrics_history = deque(maxlen=1000)
        self.app_metrics_history = deque(maxlen=1000)
        self.active_alerts = []
        self.resolved_alerts = deque(maxlen=100)
        
        # Performance counters
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.response_times = deque(maxlen=1000)
        
        # Prometheus metrics (if available)
        self.prometheus_metrics = {}
        if PROMETHEUS_AVAILABLE:
            self._initialize_prometheus_metrics()
        
        self.logger.info("Performance monitor initialized")
    
    def _load_default_config(self) -> Dict:
        """Load default monitoring configuration."""
        return {
            'collection_interval': 30,  # seconds
            'alert_check_interval': 60,  # seconds
            'prometheus_port': 9090,
            'enable_prometheus': PROMETHEUS_AVAILABLE,
            'enable_alerts': True,
            'enable_notifications': False,
            'webhook_url': os.getenv('WEBHOOK_URL'),
            'thresholds': {
                'cpu_warning': 70.0,
                'cpu_critical': 85.0,
                'memory_warning': 80.0,
                'memory_critical': 90.0,
                'disk_warning': 85.0,
                'disk_critical': 95.0,
                'response_time_warning': 2000.0,  # ms
                'response_time_critical': 5000.0,  # ms
                'error_rate_warning': 5.0,  # percent
                'error_rate_critical': 10.0,  # percent
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup dedicated performance monitoring logger."""
        logger = logging.getLogger('performance_monitor')
        logger.setLevel(logging.INFO)
        
        # File handler for performance logs
        handler = logging.FileHandler('logs/performance.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _initialize_prometheus_metrics(self):
        """Initialize Prometheus metrics collectors."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.prometheus_metrics = {
            # System metrics
            'cpu_usage': Gauge('dell_tracer_cpu_usage_percent', 'CPU usage percentage'),
            'memory_usage': Gauge('dell_tracer_memory_usage_percent', 'Memory usage percentage'),
            'disk_usage': Gauge('dell_tracer_disk_usage_percent', 'Disk usage percentage'),
            'network_bytes_sent': Counter('dell_tracer_network_bytes_sent_total', 'Network bytes sent'),
            'network_bytes_received': Counter('dell_tracer_network_bytes_received_total', 'Network bytes received'),
            
            # Application metrics
            'active_users': Gauge('dell_tracer_active_users', 'Number of active users'),
            'api_requests': Counter('dell_tracer_api_requests_total', 'Total API requests', ['endpoint', 'method']),
            'api_response_time': Histogram('dell_tracer_api_response_time_seconds', 'API response time', ['endpoint']),
            'database_connections': Gauge('dell_tracer_database_connections', 'Active database connections'),
            'switch_connections': Gauge('dell_tracer_switch_connections', 'Active switch connections'),
            'vlan_operations': Counter('dell_tracer_vlan_operations_total', 'Total VLAN operations', ['operation_type']),
            'mac_traces': Counter('dell_tracer_mac_traces_total', 'Total MAC traces', ['result_type']),
            'errors': Counter('dell_tracer_errors_total', 'Total errors', ['error_type']),
        }
        
        self.logger.info("Prometheus metrics initialized")
    
    def start_monitoring(self):
        """Start the performance monitoring system."""
        if self.running:
            self.logger.warning("Performance monitor is already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        if self.config.get('enable_prometheus') and PROMETHEUS_AVAILABLE:
            self._start_prometheus_server()
        
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop the performance monitoring system."""
        if not self.running:
            return
        
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Collect system metrics
                system_metrics = self._collect_system_metrics()
                self.system_metrics_history.append(system_metrics)
                
                # Collect application metrics
                app_metrics = self._collect_application_metrics()
                self.app_metrics_history.append(app_metrics)
                
                # Update Prometheus metrics
                if self.config.get('enable_prometheus'):
                    self._update_prometheus_metrics(system_metrics, app_metrics)
                
                # Check for alerts
                if self.config.get('enable_alerts'):
                    self._check_alerts(system_metrics, app_metrics)
                
                # Log performance summary
                self._log_performance_summary(system_metrics, app_metrics)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
            
            time.sleep(self.config['collection_interval'])
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance metrics."""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_used_percent = disk.percent
        
        # Network metrics
        network = psutil.net_io_counters()
        network_bytes_sent = network.bytes_sent
        network_bytes_recv = network.bytes_recv
        
        # Connection metrics
        connections = psutil.net_connections()
        active_connections = len([conn for conn in connections if conn.status == 'ESTABLISHED'])
        
        # Load average (Unix-like systems)
        try:
            load_average = os.getloadavg()
        except (AttributeError, OSError):
            load_average = (0.0, 0.0, 0.0)
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            disk_used_percent=disk_used_percent,
            network_bytes_sent=network_bytes_sent,
            network_bytes_recv=network_bytes_recv,
            active_connections=active_connections,
            load_average=load_average
        )
    
    def _collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-specific metrics."""
        # These would be populated by the main application
        # For now, return default values
        
        # Calculate error rate
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())
        error_rate = (total_errors / max(total_requests, 1)) * 100
        
        # Calculate average response time
        avg_response_time = sum(self.response_times) / max(len(self.response_times), 1)
        
        return ApplicationMetrics(
            timestamp=datetime.now(),
            active_users=0,  # Would be set by session tracking
            concurrent_traces=0,  # Would be set by trace tracking
            database_connections=0,  # Would be set by database monitoring
            switch_connections=0,  # Would be set by switch monitoring
            api_requests_per_minute=total_requests,
            vlan_operations_per_minute=0,  # Would be set by VLAN tracking
            error_rate_percent=error_rate,
            avg_response_time_ms=avg_response_time
        )
    
    def _update_prometheus_metrics(self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics):
        """Update Prometheus metrics with current values."""
        if not PROMETHEUS_AVAILABLE or not self.prometheus_metrics:
            return
        
        # Update system metrics
        self.prometheus_metrics['cpu_usage'].set(system_metrics.cpu_percent)
        self.prometheus_metrics['memory_usage'].set(system_metrics.memory_percent)
        self.prometheus_metrics['disk_usage'].set(system_metrics.disk_used_percent)
        
        # Update application metrics
        self.prometheus_metrics['active_users'].set(app_metrics.active_users)
        self.prometheus_metrics['database_connections'].set(app_metrics.database_connections)
        self.prometheus_metrics['switch_connections'].set(app_metrics.switch_connections)
    
    def _check_alerts(self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics):
        """Check metrics against thresholds and generate alerts."""
        thresholds = self.config['thresholds']
        
        # CPU alerts
        self._check_threshold_alert(
            'cpu_usage', system_metrics.cpu_percent,
            thresholds['cpu_warning'], thresholds['cpu_critical'],
            'CPU usage is high'
        )
        
        # Memory alerts
        self._check_threshold_alert(
            'memory_usage', system_metrics.memory_percent,
            thresholds['memory_warning'], thresholds['memory_critical'],
            'Memory usage is high'
        )
        
        # Disk alerts
        self._check_threshold_alert(
            'disk_usage', system_metrics.disk_used_percent,
            thresholds['disk_warning'], thresholds['disk_critical'],
            'Disk usage is high'
        )
        
        # Application performance alerts
        self._check_threshold_alert(
            'response_time', app_metrics.avg_response_time_ms,
            thresholds['response_time_warning'], thresholds['response_time_critical'],
            'API response time is high'
        )
        
        self._check_threshold_alert(
            'error_rate', app_metrics.error_rate_percent,
            thresholds['error_rate_warning'], thresholds['error_rate_critical'],
            'Error rate is high'
        )
    
    def _check_threshold_alert(self, metric_name: str, current_value: float,
                             warning_threshold: float, critical_threshold: float,
                             message: str):
        """Check a metric against warning and critical thresholds."""
        severity = None
        threshold = None
        
        if current_value >= critical_threshold:
            severity = 'critical'
            threshold = critical_threshold
        elif current_value >= warning_threshold:
            severity = 'warning'
            threshold = warning_threshold
        
        if severity:
            # Check if alert already exists
            existing_alert = next(
                (alert for alert in self.active_alerts 
                 if alert.metric_name == metric_name and not alert.resolved),
                None
            )
            
            if not existing_alert:
                alert = PerformanceAlert(
                    timestamp=datetime.now(),
                    alert_type='threshold',
                    severity=severity,
                    message=f"{message}: {current_value:.2f}",
                    metric_name=metric_name,
                    current_value=current_value,
                    threshold=threshold
                )
                self.active_alerts.append(alert)
                self._send_alert(alert)
        else:
            # Resolve existing alert if value is back to normal
            for alert in self.active_alerts:
                if alert.metric_name == metric_name and not alert.resolved:
                    alert.resolved = True
                    self.resolved_alerts.append(alert)
                    self.logger.info(f"Alert resolved: {alert.message}")
    
    def _send_alert(self, alert: PerformanceAlert):
        """Send alert notification."""
        self.logger.warning(f"ALERT [{alert.severity.upper()}]: {alert.message}")
        
        if self.config.get('enable_notifications') and REQUESTS_AVAILABLE:
            webhook_url = self.config.get('webhook_url')
            if webhook_url:
                try:
                    payload = {
                        'text': f"Dell Port Tracer Alert: {alert.message}",
                        'severity': alert.severity,
                        'metric': alert.metric_name,
                        'value': alert.current_value,
                        'threshold': alert.threshold,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    requests.post(webhook_url, json=payload, timeout=10)
                except Exception as e:
                    self.logger.error(f"Failed to send webhook notification: {e}")
    
    def _log_performance_summary(self, system_metrics: SystemMetrics, app_metrics: ApplicationMetrics):
        """Log performance summary."""
        self.logger.info(
            f"Performance Summary - "
            f"CPU: {system_metrics.cpu_percent:.1f}%, "
            f"Memory: {system_metrics.memory_percent:.1f}%, "
            f"Disk: {system_metrics.disk_used_percent:.1f}%, "
            f"Active Connections: {system_metrics.active_connections}, "
            f"Response Time: {app_metrics.avg_response_time_ms:.1f}ms, "
            f"Error Rate: {app_metrics.error_rate_percent:.2f}%"
        )
    
    def _start_prometheus_server(self):
        """Start Prometheus metrics server."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        try:
            prometheus_client.start_http_server(self.config['prometheus_port'])
            self.logger.info(f"Prometheus metrics server started on port {self.config['prometheus_port']}")
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus server: {e}")
    
    # Public interface methods
    
    def record_api_request(self, endpoint: str, method: str, response_time_ms: float):
        """Record API request metrics."""
        self.request_counts[f"{method}:{endpoint}"] += 1
        self.response_times.append(response_time_ms)
        
        if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
            self.prometheus_metrics['api_requests'].labels(endpoint=endpoint, method=method).inc()
            self.prometheus_metrics['api_response_time'].labels(endpoint=endpoint).observe(response_time_ms / 1000)
    
    def record_error(self, error_type: str):
        """Record application error."""
        self.error_counts[error_type] += 1
        
        if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
            self.prometheus_metrics['errors'].labels(error_type=error_type).inc()
    
    def record_vlan_operation(self, operation_type: str):
        """Record VLAN operation."""
        if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
            self.prometheus_metrics['vlan_operations'].labels(operation_type=operation_type).inc()
    
    def record_mac_trace(self, result_type: str):
        """Record MAC trace operation."""
        if PROMETHEUS_AVAILABLE and self.prometheus_metrics:
            self.prometheus_metrics['mac_traces'].labels(result_type=result_type).inc()
    
    def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        if not self.system_metrics_history or not self.app_metrics_history:
            return {'error': 'No metrics data available'}
        
        latest_system = self.system_metrics_history[-1]
        latest_app = self.app_metrics_history[-1]
        
        # Calculate averages over last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_system = [m for m in self.system_metrics_history if m.timestamp > one_hour_ago]
        recent_app = [m for m in self.app_metrics_history if m.timestamp > one_hour_ago]
        
        avg_cpu = sum(m.cpu_percent for m in recent_system) / len(recent_system) if recent_system else 0
        avg_memory = sum(m.memory_percent for m in recent_system) / len(recent_system) if recent_system else 0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'current_status': {
                'cpu_percent': latest_system.cpu_percent,
                'memory_percent': latest_system.memory_percent,
                'disk_percent': latest_system.disk_used_percent,
                'active_connections': latest_system.active_connections,
                'response_time_ms': latest_app.avg_response_time_ms,
                'error_rate_percent': latest_app.error_rate_percent
            },
            'hourly_averages': {
                'avg_cpu_percent': avg_cpu,
                'avg_memory_percent': avg_memory,
            },
            'active_alerts': len([a for a in self.active_alerts if not a.resolved]),
            'total_requests': sum(self.request_counts.values()),
            'total_errors': sum(self.error_counts.values())
        }

# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

def initialize_performance_monitoring(config: Optional[Dict] = None) -> PerformanceMonitor:
    """Initialize performance monitoring system."""
    global _performance_monitor
    _performance_monitor = PerformanceMonitor(config)
    _performance_monitor.start_monitoring()
    return _performance_monitor

if __name__ == '__main__':
    # Standalone monitoring mode
    monitor = initialize_performance_monitoring()
    
    try:
        print("🔍 Dell Port Tracer Performance Monitor")
        print("=====================================")
        print("Monitoring system performance...")
        print("Press Ctrl+C to stop")
        
        while True:
            time.sleep(10)
            report = monitor.get_performance_report()
            if 'error' not in report:
                current = report['current_status']
                print(f"CPU: {current['cpu_percent']:.1f}% | "
                      f"Memory: {current['memory_percent']:.1f}% | "
                      f"Response: {current['response_time_ms']:.0f}ms | "
                      f"Errors: {current['error_rate_percent']:.1f}%")
    
    except KeyboardInterrupt:
        print("\n⏹️  Stopping performance monitor...")
        monitor.stop_monitoring()
        print("✅ Performance monitor stopped")
