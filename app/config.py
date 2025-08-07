#!/usr/bin/env python3
"""
Configuration Management for Dell Port Tracer
=============================================

Centralized configuration management with environment-specific settings.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str
    port: int
    name: str
    user: str
    password: str
    
    @property
    def url(self) -> str:
        """Return database URL."""
        return f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}'


@dataclass
class SwitchConfig:
    """Switch connection configuration."""
    username: str
    password: str
    timeout: int = 15
    max_connections_per_switch: int = 8
    max_total_connections: int = 64
    commands_per_second_limit: int = 10


@dataclass
class AuthConfig:
    """Authentication configuration."""
    use_windows_auth: bool = False
    ad_server: str = ""
    ad_domain: str = ""
    ad_base_dn: str = ""
    local_passwords: Dict[str, str] = None
    
    def __post_init__(self):
        if self.local_passwords is None:
            self.local_passwords = {
                'oss': os.getenv('OSS_PASSWORD', 'oss123'),
                'netadmin': os.getenv('NETADMIN_PASSWORD', 'netadmin123'),
                'superadmin': os.getenv('SUPERADMIN_PASSWORD', 'superadmin123'),
                'admin': os.getenv('WEB_PASSWORD', 'password')
            }


@dataclass
class MonitoringConfig:
    """Monitoring and safety configuration."""
    cpu_green_threshold: float = 40.0
    cpu_yellow_threshold: float = 60.0
    cpu_red_threshold: float = 80.0
    syslog_enabled: bool = False
    syslog_server: str = ""
    syslog_port: int = 514


class Config:
    """Base configuration class."""
    
    def __init__(self):
        self.database = DatabaseConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            name=os.getenv('POSTGRES_DB', 'dell_port_tracer'),
            user=os.getenv('POSTGRES_USER', 'dell_tracer_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'dell_tracer_pass')
        )
        
        self.switch = SwitchConfig(
            username=os.getenv('SWITCH_USERNAME', ''),
            password=os.getenv('SWITCH_PASSWORD', ''),
            max_connections_per_switch=int(os.getenv('MAX_CONNECTIONS_PER_SWITCH', 8)),
            max_total_connections=int(os.getenv('MAX_TOTAL_CONNECTIONS', 64)),
            commands_per_second_limit=int(os.getenv('COMMANDS_PER_SECOND_LIMIT', 10))
        )
        
        self.auth = AuthConfig(
            use_windows_auth=os.getenv('USE_WINDOWS_AUTH', 'false').lower() == 'true',
            ad_server=os.getenv('AD_SERVER', ''),
            ad_domain=os.getenv('AD_DOMAIN', ''),
            ad_base_dn=os.getenv('AD_BASE_DN', '')
        )
        
        self.monitoring = MonitoringConfig(
            cpu_green_threshold=float(os.getenv('CPU_GREEN_THRESHOLD', 40)),
            cpu_yellow_threshold=float(os.getenv('CPU_YELLOW_THRESHOLD', 60)),
            cpu_red_threshold=float(os.getenv('CPU_RED_THRESHOLD', 80)),
            syslog_enabled=os.getenv('SYSLOG_ENABLED', 'false').lower() == 'true',
            syslog_server=os.getenv('SYSLOG_SERVER', ''),
            syslog_port=int(os.getenv('SYSLOG_PORT', 514))
        )
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        if not self.switch.username or not self.switch.password:
            errors.append("Switch credentials (SWITCH_USERNAME, SWITCH_PASSWORD) are required")
        
        if self.auth.use_windows_auth:
            if not self.auth.ad_server:
                errors.append("AD_SERVER is required when USE_WINDOWS_AUTH is true")
            if not self.auth.ad_domain:
                errors.append("AD_DOMAIN is required when USE_WINDOWS_AUTH is true")
        
        if errors:
            for error in errors:
                print(f"❌ Configuration Error: {error}")
            return False
        
        return True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    
    def __init__(self):
        super().__init__()
        # Override database for testing
        self.database = DatabaseConfig(
            host='localhost',
            port=5432,
            name='test_dell_port_tracer',
            user='test_user',
            password='test_password'
        )


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env_name: str = None) -> Config:
    """Get configuration for environment."""
    if env_name is None:
        env_name = os.getenv('FLASK_ENV', 'default')
    
    return config.get(env_name, config['default'])()
