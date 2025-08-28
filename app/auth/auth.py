#!/usr/bin/env python3
"""
Authentication Module for Dell Switch Port Tracer
=================================================

This module handles user authentication for the Dell Switch Port Tracer application,
supporting both Windows Active Directory integration and local user accounts.

Features:
- Windows AD authentication with LDAP3
- Local user account fallback
- Role-based access control (OSS, NetAdmin, SuperAdmin)
- Comprehensive audit logging
- Security group mapping

Author: Network Operations Team
Version: 2.1.3
Last Updated: August 2025
"""

import os
import logging
from typing import Optional, Dict, Any

# Import Windows Authentication
try:
    import ldap3
    from nt_auth_integration import WindowsAuthenticator, AD_CONFIG
    WINDOWS_AUTH_AVAILABLE = True
except ImportError:
    WINDOWS_AUTH_AVAILABLE = False
    print("Warning: ldap3 not installed. Windows authentication disabled.")

# Configure logger
logger = logging.getLogger(__name__)

# User roles and credentials
USERS = {
    'oss': {'password': os.getenv('OSS_PASSWORD', 'oss123'), 'role': 'oss'},
    'netadmin': {'password': os.getenv('NETADMIN_PASSWORD', 'netadmin123'), 'role': 'netadmin'},
    'superadmin': {'password': os.getenv('SUPERADMIN_PASSWORD', 'superadmin123'), 'role': 'superadmin'},
    # Legacy admin user (maps to superadmin)
    'admin': {'password': os.getenv('WEB_PASSWORD', 'password'), 'role': 'superadmin'}
}

# Role permissions
ROLE_PERMISSIONS = {
    'oss': {
        'show_vlan_details': False,  # Only for access ports
        'show_uplink_ports': False,  # Hide uplink ports
        'show_trunk_general_vlans': False,  # Hide VLAN details for trunk/general
        'show_switch_names': False  # Hide switch names for security
    },
    'netadmin': {
        'show_vlan_details': True,
        'show_uplink_ports': True,
        'show_trunk_general_vlans': True,
        'show_switch_names': True  # Show actual switch names
    },
    'superadmin': {
        'show_vlan_details': True,
        'show_uplink_ports': True,
        'show_trunk_general_vlans': True,
        'show_switch_names': True  # Show actual switch names
    }
}


def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify user credentials against Windows AD or local accounts.
    
    Args:
        username (str): Username to authenticate
        password (str): Password for authentication
        
    Returns:
        dict: User information if authentication successful, None otherwise
              Contains: username, display_name, role, auth_method
    """
    # Try Windows Authentication first if enabled
    use_windows_auth = os.getenv('USE_WINDOWS_AUTH', 'false').lower() == 'true'
    
    if use_windows_auth and WINDOWS_AUTH_AVAILABLE:
        try:
            # Configure Active Directory settings from environment variables
            ad_config = {
                'server': os.getenv('AD_SERVER', 'ldap://kmc.int'),
                'domain': os.getenv('AD_DOMAIN', 'kmc.int'),
                'base_dn': os.getenv('AD_BASE_DN', 'DC=kmc,DC=int'),
                'user_search_base': os.getenv('AD_USER_SEARCH_BASE', 'DC=kmc,DC=int'),
                'group_search_base': os.getenv('AD_GROUP_SEARCH_BASE', 'DC=kmc,DC=int'),
                'required_group': os.getenv('AD_REQUIRED_GROUP')
            }
            
            authenticator = WindowsAuthenticator(ad_config)
            user_info = authenticator.authenticate_user(username, password)
            
            if user_info:
                # Map AD security groups to application roles (least privilege default)
                role = 'oss'  # Default role for all Windows users
                
                if user_info.get('groups'):
                    groups = [str(group).upper() for group in user_info['groups']]
                    
                    # Debug logging for group membership
                    logger.info(f"User {username} AD groups: {groups}")
                    
                    # Role assignment based on specific AD security groups
                    # Check for exact group CN (Common Name) matches, not just substring matches
                    oss_group_found = any('CN=SOLARWINDS_OSS/SD_ACCESS' in group or 'CN=SOLARWINDS_OSS_SD_ACCESS' in group for group in groups)
                    noc_team_group_found = any('CN=NOC TEAM' in group for group in groups)
                    admin_group_found = any('CN=ADMIN' in group or 'CN=SUPERADMIN' in group for group in groups)
                    
                    if oss_group_found:
                        role = 'oss'
                        logger.info(f"User {username} assigned role 'oss' due to SOLARWINDS_OSS/SD_ACCESS group")
                    elif noc_team_group_found:
                        role = 'netadmin'
                        logger.info(f"User {username} assigned role 'netadmin' due to NOC TEAM group")
                    elif admin_group_found:
                        role = 'superadmin'
                        logger.info(f"User {username} assigned role 'superadmin' due to admin group")
                    else:
                        logger.info(f"User {username} assigned default role 'oss' - no matching groups found")
                
                return {
                    'username': user_info['username'],
                    'display_name': user_info.get('display_name', username),
                    'role': role,
                    'auth_method': 'windows_ad'
                }
        except Exception as e:
            logger.warning(f"Windows authentication failed for {username}: {str(e)}")
            # Fall through to local authentication
    
    # Fall back to local user authentication
    if username in USERS:
        user_info = USERS[username]
        if user_info['password'] == password:
            return {
                'username': username, 
                'role': user_info['role'],
                'auth_method': 'local'
            }
    
    return None


def get_user_permissions(role: str) -> Dict[str, Any]:
    """Get permissions for a user role.
    
    Args:
        role (str): User role (oss, netadmin, superadmin)
        
    Returns:
        dict: Role permissions configuration
    """
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS['oss'])


def is_authorized_for_endpoint(role: str, endpoint: str) -> bool:
    """Check if a user role is authorized for a specific endpoint.
    
    Args:
        role (str): User role
        endpoint (str): Flask endpoint name
        
    Returns:
        bool: True if authorized, False otherwise
    """
    # Define endpoint access levels
    PUBLIC_ENDPOINTS = ['login', 'logout', 'health']
    OSS_ENDPOINTS = ['index', 'trace']
    ADMIN_ENDPOINTS = ['inventory', 'vlan', 'api_*']  # API endpoints require admin access
    
    if endpoint in PUBLIC_ENDPOINTS:
        return True
    
    if role == 'oss' and endpoint in OSS_ENDPOINTS:
        return True
    
    if role in ['netadmin', 'superadmin']:
        return True  # Full access for admin roles
    
    return False


def require_role(*allowed_roles):
    """Decorator to require specific roles for route access.
    
    Args:
        *allowed_roles: Tuple of allowed role names
        
    Returns:
        Function decorator
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from flask import session, jsonify
            
            if 'username' not in session:
                return jsonify({'error': 'Not authenticated'}), 401
            
            user_role = session.get('role', 'oss')
            if user_role not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
