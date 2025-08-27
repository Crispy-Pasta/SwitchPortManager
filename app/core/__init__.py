"""
Core functionality module for Dell Switch Port Tracer

Contains database management, switch communication, VLAN management,
and utility functions.
"""

from .database import init_db, get_db_connection
from .switch_manager import DellSwitchSSH
from .vlan_manager import VLANManager
from .utils import is_valid_mac, get_mac_format_error_message

__all__ = [
    "init_db", 
    "get_db_connection",
    "DellSwitchSSH", 
    "VLANManager", 
    "is_valid_mac", 
    "get_mac_format_error_message"
]
