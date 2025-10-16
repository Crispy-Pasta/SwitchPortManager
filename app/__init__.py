"""
Dell Switch Port Tracer Application Package

This package contains the Dell Switch Port Tracer web application for managing
Dell N2000/N3000/N3200 series switches with enhanced VLAN management capabilities.

Version: 2.2.4
"""

__version__ = "2.2.4"
__title__ = "Dell Switch Port Tracer"
__description__ = "Web-based port tracing and VLAN management for Dell switches"
__author__ = "Dell Port Tracer Team"

# Import core modules for easier access
from .core.database import init_db
from .core.utils import get_version

__all__ = ["init_db", "get_version", "__version__"]
