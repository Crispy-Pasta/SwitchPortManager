#!/usr/bin/env python3
"""
Advanced Logging and Error Handling Utilities
==============================================

Centralized logging configuration with structured logging,
error tracking, and performance monitoring.
"""

import logging
import logging.handlers
import json
import time
import traceback
import functools
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Enhanced log levels."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    AUDIT = 35  # Custom level for audit events


@dataclass
class LogEvent:
    """Structured log event."""
    timestamp: str
    level: str
    logger: str
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    switch_ip: Optional[str] = None
    duration_ms: Optional[float] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record):
        """Format log record as structured JSON."""
        log_event = LogEvent(
            timestamp=datetime.utcnow().isoformat() + 'Z',
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            extra_data=getattr(record, 'extra_data', None)
        )
        
        # Add exception information if present
        if record.exc_info:
            log_event.error_type = record.exc_info[0].__name__
            log_event.stack_trace = self.formatException(record.exc_info)
        
        # Add custom fields if present
        for field in ['user_id', 'session_id', 'request_id', 'ip_address', 
                      'user_agent', 'switch_ip', 'duration_ms']:
            if hasattr(record, field):
                setattr(log_event, field, getattr(record, field))
        
        return json.dumps(asdict(log_event), ensure_ascii=False)


class PerformanceLogger:
    """Performance monitoring and logging."""
    
    def __init__(self, logger_name: str = 'performance'):
        self.logger = logging.getLogger(logger_name)
    
    def time_operation(self, operation_name: str, user_id: str = None, 
                      switch_ip: str = None):
        """Decorator to time operations."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    extra = {
                        'operation': operation_name,
                        'duration_ms': round(duration_ms, 2),
                        'status': 'success'
                    }
                    
                    if user_id:
                        extra['user_id'] = user_id
                    if switch_ip:
                        extra['switch_ip'] = switch_ip
                    
                    self.logger.info(
                        f"{operation_name} completed successfully",
                        extra={'extra_data': extra}
                    )
                    
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    extra = {
                        'operation': operation_name,
                        'duration_ms': round(duration_ms, 2),
                        'status': 'error',
                        'error': str(e)
                    }
                    
                    if user_id:
                        extra['user_id'] = user_id
                    if switch_ip:
                        extra['switch_ip'] = switch_ip
                    
                    self.logger.error(
                        f"{operation_name} failed",
                        extra={'extra_data': extra},
                        exc_info=True
                    )
                    
                    raise
                    
            return wrapper
        return decorator


class SecurityLogger:
    """Security event logging."""
    
    def __init__(self, logger_name: str = 'security'):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(LogLevel.AUDIT.value)
    
    def log_login_attempt(self, username: str, success: bool, ip_address: str = None,
                         user_agent: str = None, auth_method: str = 'local'):
        """Log authentication attempts."""
        status = "SUCCESS" if success else "FAILED"
        message = f"Login {status} - User: {username}, Method: {auth_method}"
        
        extra = {
            'event_type': 'authentication',
            'username': username,
            'success': success,
            'auth_method': auth_method,
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, message, extra={'extra_data': extra})
    
    def log_access_attempt(self, username: str, resource: str, success: bool,
                          ip_address: str = None, reason: str = None):
        """Log resource access attempts."""
        status = "GRANTED" if success else "DENIED"
        message = f"Access {status} - User: {username}, Resource: {resource}"
        
        if reason:
            message += f", Reason: {reason}"
        
        extra = {
            'event_type': 'access_control',
            'username': username,
            'resource': resource,
            'success': success,
            'reason': reason,
            'ip_address': ip_address
        }
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, message, extra={'extra_data': extra})
    
    def log_switch_operation(self, username: str, switch_ip: str, 
                           operation: str, success: bool, details: str = None):
        """Log switch operations."""
        status = "SUCCESS" if success else "FAILED"
        message = f"Switch Operation {status} - User: {username}, Switch: {switch_ip}, Operation: {operation}"
        
        if details:
            message += f", Details: {details}"
        
        extra = {
            'event_type': 'switch_operation',
            'username': username,
            'switch_ip': switch_ip,
            'operation': operation,
            'success': success,
            'details': details
        }
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, message, extra={'extra_data': extra})


class LoggingManager:
    """Centralized logging management."""
    
    def __init__(self, app_name: str = 'dell_port_tracer'):
        self.app_name = app_name
        self.loggers = {}
        
        # Add custom log level
        logging.addLevelName(LogLevel.AUDIT.value, 'AUDIT')
        logging.addLevelName(LogLevel.TRACE.value, 'TRACE')
    
    def setup_logging(self, log_level: str = 'INFO', 
                     enable_file_logging: bool = True,
                     enable_syslog: bool = False,
                     syslog_server: str = None,
                     syslog_port: int = 514,
                     log_file_path: str = 'logs/app.log'):
        """Configure application logging."""
        
        # Create logs directory if it doesn't exist
        import os
        os.makedirs('logs', exist_ok=True)
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        handlers = []
        
        # Console handler with structured format
        console_handler = logging.StreamHandler()
        console_formatter = StructuredFormatter()
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
        
        # File handler for persistent logging
        if enable_file_logging:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=10
            )
            file_formatter = StructuredFormatter()
            file_handler.setFormatter(file_formatter)
            handlers.append(file_handler)
        
        # Syslog handler for centralized logging
        if enable_syslog and syslog_server:
            try:
                syslog_handler = logging.handlers.SysLogHandler(
                    address=(syslog_server, syslog_port),
                    facility=logging.handlers.SysLogHandler.LOG_LOCAL0
                )
                syslog_formatter = logging.Formatter(
                    f'{self.app_name}[%(process)d]: %(levelname)s - %(message)s'
                )
                syslog_handler.setFormatter(syslog_formatter)
                handlers.append(syslog_handler)
                
                logging.info(f"Syslog logging enabled: {syslog_server}:{syslog_port}")
                
            except Exception as e:
                logging.warning(f"Failed to setup syslog handler: {e}")
        
        # Add all handlers to root logger
        for handler in handlers:
            root_logger.addHandler(handler)
        
        # Create specialized loggers
        self.loggers['app'] = logging.getLogger('app')
        self.loggers['security'] = SecurityLogger()
        self.loggers['performance'] = PerformanceLogger()
        
        logging.info(f"Logging configured - Level: {log_level}, Handlers: {len(handlers)}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a named logger."""
        if name not in self.loggers:
            self.loggers[name] = logging.getLogger(name)
        
        return self.loggers[name]
    
    def log_application_start(self, version: str, config_summary: Dict[str, Any]):
        """Log application startup with configuration summary."""
        app_logger = self.get_logger('app')
        
        extra = {
            'event_type': 'application_lifecycle',
            'action': 'start',
            'version': version,
            'config': config_summary
        }
        
        app_logger.info(
            f"Dell Port Tracer v{version} starting",
            extra={'extra_data': extra}
        )
    
    def log_application_stop(self, version: str):
        """Log application shutdown."""
        app_logger = self.get_logger('app')
        
        extra = {
            'event_type': 'application_lifecycle',
            'action': 'stop',
            'version': version
        }
        
        app_logger.info(
            f"Dell Port Tracer v{version} shutting down",
            extra={'extra_data': extra}
        )
