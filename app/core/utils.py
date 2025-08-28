#!/usr/bin/env python3
"""
Utilities Module for Dell Switch Port Tracer
============================================

This module contains common utility functions and helpers for the
Dell Switch Port Tracer application.

Features:
- MAC address validation and formatting
- Switch data formatting
- Role-based filtering utilities
- Validation helpers
- Error message generators

Author: Network Operations Team
Version: 2.1.3
Last Updated: August 2025
"""

import re
import logging
from typing import Dict, List, Any, Optional
from app.core.database import Site, Floor, Switch
from app.auth.auth import get_user_permissions

# Configure logger
logger = logging.getLogger(__name__)


def is_valid_mac(mac: str) -> bool:
    """Validate MAC address format to prevent command injection attacks.
    
    This function provides comprehensive MAC address validation using strict regex patterns
    to ensure only legitimate MAC address formats are accepted. This prevents command
    injection attempts through malformed MAC address inputs.
    
    Args:
        mac (str): MAC address string to validate
        
    Returns:
        bool: True if MAC address format is valid, False otherwise
        
    Supported Formats:
        - Colon-separated: 00:1B:63:84:45:E6
        - Hyphen-separated: 00-1B-63-84-45-E6  
        - Continuous format: 001B638445E6
        
    Security Features:
        - Strict regex validation prevents injection attacks
        - Only hexadecimal characters (0-9, A-F, a-f) allowed
        - Exact length enforcement (12 hex characters)
        - No special characters except colons and hyphens in specific positions
    """
    # Comprehensive regex pattern for MAC address validation:
    # - ([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}) matches colon/hyphen separated format
    # - ([0-9A-Fa-f]{12}) matches continuous 12-character format
    pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^([0-9A-Fa-f]{12})$')
    return pattern.match(mac)


def get_mac_format_error_message(mac: str) -> Dict[str, Any]:
    """Generate a security-focused error message for invalid MAC address formats.
    
    This function creates user-friendly error messages that provide helpful guidance
    for entering valid MAC addresses while maintaining security best practices.
    
    Security Features:
        - Only displays valid format examples (no incorrect/malicious examples)
        - Excludes potentially harmful input patterns from error messages
        - Provides educational content without exposing attack vectors
        - Maintains user experience while prioritizing security
    
    Args:
        mac (str): The invalid MAC address that was provided by the user
        
    Returns:
        dict: Structured error response containing:
            - error: Brief error description
            - details: Comprehensive information including:
                - provided: The user's original input (for context)
                - valid_formats: List of supported MAC address formats
                - requirements: Technical requirements for valid MAC addresses
                - examples: Only correct examples to guide proper usage
                
    Note:
        This function intentionally excludes incorrect examples and security
        warnings to prevent exposing potential attack patterns to users.
    """
    return {
        'error': 'Invalid MAC address format',
        'details': {
            'provided': mac,
            'valid_formats': [
                'Colon-separated: 00:1B:63:84:45:E6',
                'Hyphen-separated: 00-1B-63-84-45-E6', 
                'Continuous format: 001B638445E6'
            ],
            'requirements': [
                'Must be exactly 12 hexadecimal characters (0-9, A-F)',
                'Case insensitive (both uppercase and lowercase accepted)',
                'No special characters except colons (:) or hyphens (-)'
            ],
            'examples': {
                'correct': [
                    '00:1B:63:84:45:E6',
                    '00-1B-63-84-45-E6',
                    '001B638445E6',
                    'aa:bb:cc:dd:ee:ff',
                    'AA-BB-CC-DD-EE-FF'
                ]
            }
        }
    }


def format_switches_for_frontend(user_role: str = 'oss') -> Dict[str, Any]:
    """Convert PostgreSQL database format for frontend consumption.
    
    Args:
        user_role (str): User role for filtering (currently not used in data structure)
        
    Returns:
        dict: Formatted switches data structure for frontend
    """
    try:
        # Query PostgreSQL database for all sites with floors and switches
        sites = Site.query.all()
        formatted_sites = []
        
        for site in sites:
            floors = []
            for floor in site.floors:
                switches = []
                # Only include enabled switches
                enabled_switches = [s for s in floor.switches if s.enabled]
                
                for switch in enabled_switches:
                    # Always use actual switch names in data structure
                    # Role-based filtering will be handled in frontend JavaScript
                    switches.append({
                        'name': switch.name,
                        'ip': switch.ip_address,
                        'model': switch.model or 'Unknown',
                        'description': switch.description or ''
                    })
                
                if switches:  # Only include floors with enabled switches
                    floors.append({
                        'floor': floor.name,
                        'switches': switches
                    })
            
            if floors:  # Only include sites with floors that have switches
                formatted_sites.append({
                    'name': site.name,
                    'location': f"{site.name.upper()} Site",
                    'floors': floors
                })
        
        return {'sites': formatted_sites}
        
    except Exception as e:
        logger.error(f"Database error in format_switches_for_frontend: {str(e)}")
        return {'sites': []}


def get_site_floor_switches(site: str, floor: str) -> List[Dict[str, Any]]:
    """Get switches for specific site and floor from database.
    
    Args:
        site (str): Site name
        floor (str): Floor name
        
    Returns:
        list: List of switch dictionaries with name, ip, site, floor
    """
    try:
        # Query database for switches
        site_obj = Site.query.filter_by(name=site).first()
        if not site_obj:
            return []
            
        floor_obj = Floor.query.filter_by(site_id=site_obj.id, name=floor).first()
        if not floor_obj:
            return []
            
        switches = Switch.query.filter_by(floor_id=floor_obj.id, enabled=True).all()
        
        matching_switches = []
        for switch in switches:
            matching_switches.append({
                'name': switch.name,
                'ip': switch.ip_address,
                'site': site,
                'floor': floor
            })
        
        return matching_switches
    except Exception as e:
        logger.error(f"Database error in get_site_floor_switches: {str(e)}")
        return []


def apply_role_based_filtering(results: List[Dict[str, Any]], user_role: str) -> List[Dict[str, Any]]:
    """Apply role-based filtering to trace results.
    
    Args:
        results (list): List of trace results
        user_role (str): User role (oss, netadmin, superadmin)
        
    Returns:
        list: Filtered results based on user permissions
    """
    from app.core.switch_manager import is_uplink_port, detect_switch_model_from_config
    
    permissions = get_user_permissions(user_role)
    filtered_results = []
    
    for result in results:
        if result['status'] != 'found':
            filtered_results.append(result)
            continue
            
        # For OSS users, filter out uplink ports
        if not permissions['show_uplink_ports']:
            # Detect switch model from database first, then fallback to configuration
            switch_model = 'N3000'  # Default fallback
            try:
                # Try to get switch model from database
                switch_obj = Switch.query.filter_by(ip_address=result['switch_ip']).first()
                if switch_obj and switch_obj.model:
                    # Use database switch model directly
                    switch_model = detect_switch_model_from_config(switch_obj.name, {'model': switch_obj.model})
            except Exception as e:
                logger.debug(f"Could not detect switch model for {result['switch_ip']}: {str(e)}")
            
            if is_uplink_port(result['port'], switch_model, result.get('port_description', '')):
                # Skip uplink ports for OSS users
                continue
        
        # Apply VLAN filtering based on port mode and role
        if result.get('port_mode') in ['trunk', 'general'] and not permissions['show_trunk_general_vlans']:
            # For OSS users on trunk/general ports, hide VLAN details
            result_copy = result.copy()
            result_copy['vlan_restricted'] = True
            result_copy['restriction_message'] = 'Please contact network admin for VLAN details'
            # Clear VLAN details
            result_copy['port_pvid'] = ''
            result_copy['port_vlans'] = []
            filtered_results.append(result_copy)
        else:
            # Show full details for access ports or privileged users
            filtered_results.append(result)
    
    return filtered_results


def load_switches_from_database() -> Dict[str, Any]:
    """Load switches from PostgreSQL database.
    
    Returns:
        dict: Sites configuration structure
    """
    try:
        sites_with_switches = {}
        sites = Site.query.all()
        for site in sites:
            floors = Floor.query.filter_by(site_id=site.id).all()
            floors_with_switches = {}
            for floor in floors:
                switches = Switch.query.filter_by(floor_id=floor.id, enabled=True).all()
                switch_data = [{'name': sw.name, 'ip': sw.ip_address} for sw in switches]
                if switch_data:
                    floors_with_switches[floor.name] = switch_data
            if floors_with_switches:
                sites_with_switches[site.name] = floors_with_switches
        if not sites_with_switches:
            return {"sites": []}
        else:
            return {"sites": sites_with_switches}
    except Exception as e:
        logger.error(f"Failed to load switches from the database: {str(e)}")
        return {"sites": []}


def get_version() -> str:
    """Get application version.
    
    Returns:
        str: Application version string
    """
    return "2.1.3"
