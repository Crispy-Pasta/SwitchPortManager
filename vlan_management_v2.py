#!/usr/bin/env python3
"""
Advanced VLAN Management System for Dell Switches (Enhanced)
===========================================================

Comprehensive VLAN management with safety checks, port validation, and user confirmations.
Supports N2000, N3000, and N3200 Dell switch models with proper uplink protection.

CORE FEATURES:
- Database-driven switch selection with searchable dropdown
- Multi-port input with validation and safety checks  
- Port status and mode verification with user confirmations
- VLAN existence checking with auto-creation capability
- Uplink port protection (prevents changes to uplink ports)
- Force change and skip options with proper confirmations
- Comprehensive audit logging for all operations

NEW ENHANCED FEATURES (v2.1.3):
- Interface Range Optimization: Groups consecutive ports for efficient batch operations
- Intelligent Fallback System: Automatically switches from range to individual port config
- Enhanced Success Response: Detailed feedback with ranges used and descriptions applied
- Robust Error Handling: Multi-layer fallback with comprehensive error detection
- Dell N2048 Compatibility: Special handling for switch-specific limitations
- Advanced Debugging: Extensive logging for troubleshooting VLAN operations
- Port Description Management: Applies descriptions alongside VLAN changes

UI/UX IMPROVEMENTS:
- Enhanced VLAN naming conventions with enterprise standards
- Updated placeholder examples: Zone_Client_Name, Internal_Network, Guest_Access, IoT_Devices
- Improved help text with naming guidelines for consistency
- Better user guidance for VLAN naming best practices and standardization
- Detailed success messages showing optimization results

COMPREHENSIVE TROUBLESHOOTING GUIDE:
=================================
DEBUGGING VLAN OPERATIONS:
- Check logs for "Generated interface ranges" to see optimization attempts
- Look for "Falling back to individual port configuration" for compatibility issues  
- Monitor "Batch operation complete" messages for operation results
- Use DEBUG level logging for detailed command execution traces
- Search for "VLAN_MANAGER" in logs for all VLAN-related activities

COMMON ISSUES AND SOLUTIONS:
1. CONNECTION PROBLEMS:
   - Verify SWITCH_USERNAME and SWITCH_PASSWORD environment variables
   - Check switch SSH access: Dell switches limit to 10 concurrent sessions
   - Ensure switch IP is reachable: ping test before VLAN operations
   - Monitor "SSH connection failed" errors in port_tracer.log

2. AUTHENTICATION ERRORS:
   - Check switch credentials in environment variables
   - Verify user has necessary switch privileges (enable mode access)
   - Look for "Authentication failed" in logs
   - Ensure switch user account is not locked or expired

3. VLAN OPERATION FAILURES:
   - Check VLAN exists: Use VLAN check API before assignment
   - Verify port is not in trunk/general mode (access ports only)
   - Look for uplink port protection warnings in logs
   - Check for existing VLAN assignments that prevent changes

4. PORT VALIDATION ERRORS:
   - Use exact Dell format: Gi1/0/24, Te1/0/1, Tw1/0/1
   - Verify stack/module/port numbers match switch hardware
   - Check for typos in port specifications
   - Review port range syntax: Gi1/0/1-5 (not Gi1/0/1-Gi1/0/5)

5. MODEL-SPECIFIC ISSUES:
   - Dell N2048: Limited interface range support, falls back to individual config
   - Dell N3000: Full feature support, should use optimized ranges
   - Check "Switch model detected" logs for compatibility mode

LOG LOCATIONS AND MONITORING:
- System logs: port_tracer.log (all operations and errors)
- Audit logs: audit.log (user actions and security events)
- VLAN specific: Search for "VLAN_MANAGER" prefix in logs
- Debug mode: Set LOG_LEVEL=DEBUG for detailed SSH command traces

SUPPORTED SWITCH MODELS:
- Dell N2000 Series (N2048, N2024, etc.) - Special compatibility mode
- Dell N3000 Series - Full feature support
- Dell N3200 Series - Full feature support

AUTHORS: Network Operations Team
VERSION: 2.1.3 (Enhanced VLAN Management with Interface Range Optimization)
LAST UPDATED: 2025-08-07
COMPATIBILITY: Python 3.7+, Dell PowerConnect N-Series Switches
"""

import paramiko
import logging
import re
import time
from datetime import datetime
from flask import Flask, jsonify, request, session
from database import db, Switch, Site, Floor
import json

# Configure logging
logger = logging.getLogger(__name__)

# Security validation functions for VLAN Manager inputs
def is_valid_port_input(port_input):
    """
    Validate port input format to prevent command injection attacks in VLAN operations.
    
    This function provides comprehensive port format validation using strict patterns
    to ensure only legitimate Dell switch port formats are accepted. This prevents
    command injection attempts through malformed port specifications.
    
    Args:
        port_input (str): Port specification string to validate
        
    Returns:
        bool: True if port input format is valid, False otherwise
        
    Supported Formats:
        - Single ports: Gi1/0/24, Te1/0/1, Tw1/0/1
        - Port ranges: Gi1/0/1-5, Te1/0/1-4
        - Multiple entries: Gi1/0/1,Gi1/0/5,Te1/0/1
        - Mixed formats: Gi1/0/1-5,Te1/0/10,Tw1/0/1-2
        
    Security Features:
        - Strict regex validation prevents injection attacks
        - Only allows Dell switch interface naming conventions
        - Validates port numbers within realistic ranges
        - Prevents special characters except allowed delimiters
    """
    if not port_input or not isinstance(port_input, str):
        return False
    
    port_input = port_input.strip()
    if not port_input:
        return False
    
    # Split by commas for multiple port entries
    port_parts = [part.strip() for part in port_input.split(',')]
    
    for part in port_parts:
        if not part:
            continue
            
        # Check for port ranges (e.g., "Gi1/0/1-5" or "Gi1/0/1-Gi1/0/5")
        if '-' in part:
            if part.count('-') != 1:
                return False
            
            start_port, end_port = part.split('-')
            start_port = start_port.strip()
            end_port = end_port.strip()
            
            # Validate both parts of the range
            if not _is_valid_single_port(start_port):
                return False
            
            # End port can be just a number for shorthand notation (Gi1/0/1-5)
            if not _is_valid_single_port(end_port) and not _is_valid_port_number(end_port):
                return False
        else:
            # Single port validation
            if not _is_valid_single_port(part):
                return False
    
    return True

def _is_valid_single_port(port):
    """Validate a single port specification."""
    # Dell switch port format: Interface[stack]/[module]/[port]
    # Examples: Gi1/0/24, Te1/0/1, Tw1/0/1
    pattern = re.compile(r'^(Gi|gi|Te|te|Tw|tw)(\d{1,2})/(\d{1,2})/(\d{1,3})$')
    match = pattern.match(port.strip())
    
    if not match:
        return False
    
    # Extract components for range validation
    interface_type, stack, module, port_num = match.groups()
    
    # Validate ranges (realistic Dell switch limits)
    stack_num = int(stack)
    module_num = int(module)
    port_number = int(port_num)
    
    # Stack: 1-8 (typical Dell switch stack range)
    # Module: 0-3 (typical module range) 
    # Port: 1-128 (generous range covering most Dell models)
    return (1 <= stack_num <= 8 and 
            0 <= module_num <= 3 and 
            1 <= port_number <= 128)

def _is_valid_port_number(port_num_str):
    """Validate a port number string (for range notation)."""
    try:
        port_num = int(port_num_str)
        return 1 <= port_num <= 128
    except ValueError:
        return False

def is_valid_port_description(description):
    """
    Validate port description to prevent command injection and ensure safe content.
    
    This function ensures port descriptions are safe for use in Dell switch CLI
    commands while allowing legitimate business content.
    
    Args:
        description (str): Port description to validate
        
    Returns:
        bool: True if description is valid and safe, False otherwise
        
    Security Features:
        - Prevents command injection through special characters
        - Blocks suspicious command sequences
        - Allows standard alphanumeric and business-safe characters
        - Enforces reasonable length limits
    """
    if not isinstance(description, str):
        return False
    
    description = description.strip()
    
    # Allow empty descriptions
    if not description:
        return True
    
    # Length validation (reasonable for switch port descriptions)
    if len(description) > 200:
        return False
    
    # Character validation: Allow alphanumeric, spaces, and safe punctuation
    # Exclude potentially dangerous characters for CLI commands
    allowed_pattern = re.compile(r'^[a-zA-Z0-9\s\-_.,()\[\]#@+=:]*$')
    if not allowed_pattern.match(description):
        return False
    
    # Block suspicious command sequences and injection patterns
    dangerous_patterns = [
        # Command separators and operators
        ';', '|', '&', '$', '`', '\\', '"', "'",
        # Common injection keywords
        'configure', 'exit', 'enable', 'disable',
        'shutdown', 'no shutdown', 'reload', 'delete',
        'vlan', 'interface', 'switchport', 'access',
        # Script execution patterns
        '$(', '${', '%%', '<script', '</script',
        # Network command patterns
        'ping', 'traceroute', 'telnet', 'ssh'
    ]
    
    description_lower = description.lower()
    for pattern in dangerous_patterns:
        if pattern in description_lower:
            return False
    
    return True

def is_valid_vlan_id(vlan_id):
    """
    Validate VLAN ID to ensure it's within IEEE 802.1Q standard ranges.
    
    This function validates VLAN IDs according to IEEE standards and prevents
    injection attacks through malformed VLAN specifications.
    
    Args:
        vlan_id (str or int): VLAN ID to validate
        
    Returns:
        bool: True if VLAN ID is valid, False otherwise
        
    Valid Range:
        - 1-4094 (IEEE 802.1Q standard range)
        - Excludes reserved VLANs (0, 4095)
        
    Security Features:
        - Strict numeric validation prevents injection
        - Range enforcement follows IEEE standards
        - Input sanitization for type safety
    """
    try:
        # Handle both string and integer inputs
        if isinstance(vlan_id, str):
            vlan_id = vlan_id.strip()
            if not vlan_id.isdigit():
                return False
            vlan_num = int(vlan_id)
        elif isinstance(vlan_id, int):
            vlan_num = vlan_id
        else:
            return False
        
        # IEEE 802.1Q standard VLAN range: 1-4094
        # VLAN 0 and 4095 are reserved
        return 1 <= vlan_num <= 4094
        
    except (ValueError, TypeError):
        return False

def is_valid_vlan_name(vlan_name):
    """
    Validate VLAN name to prevent command injection and ensure compliance with
    Dell switch naming conventions and business standards.
    
    This function ensures VLAN names are safe for CLI commands while supporting
    enterprise naming conventions and standards.
    
    Args:
        vlan_name (str): VLAN name to validate
        
    Returns:
        bool: True if VLAN name is valid and safe, False otherwise
        
    Naming Standards:
        - Supports enterprise conventions (Zone_Client_Name, Internal_Network)
        - Alphanumeric characters with underscores and hyphens
        - Reasonable length limits for switch compatibility
        
    Security Features:
        - Prevents command injection through special characters
        - Blocks suspicious command sequences
        - Enforces Dell switch naming compatibility
        - Validates against reserved or dangerous names
    """
    if not isinstance(vlan_name, str):
        return False
    
    vlan_name = vlan_name.strip()
    
    # VLAN name is required and cannot be empty
    if not vlan_name:
        return False
    
    # Length validation (Dell switch VLAN name limits)
    if len(vlan_name) > 64:  # Conservative limit for Dell switches
        return False
    
    # Character validation: Enterprise-friendly naming convention
    # Allow alphanumeric, underscores, hyphens, and limited punctuation
    allowed_pattern = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-_.]*$')
    if not allowed_pattern.match(vlan_name):
        return False
    
    # Block dangerous or reserved names
    dangerous_names = [
        # Switch configuration keywords
        'configure', 'exit', 'enable', 'disable', 'interface',
        'switchport', 'access', 'trunk', 'general', 'native',
        # System reserved names
        'default', 'management', 'system', 'admin', 'root',
        # Command injection attempts
        'config', 'conf', 'term', 'terminal', 'global',
        # Common attack patterns
        'script', 'exec', 'eval', 'cmd', 'command'
    ]
    
    vlan_name_lower = vlan_name.lower()
    for dangerous_name in dangerous_names:
        if dangerous_name == vlan_name_lower:
            return False
    
    # Block names that start with numbers only (some switches don't allow this)
    if vlan_name[0].isdigit() and vlan_name.isdigit():
        return False
    
    return True

def get_port_format_error_message(port_input):
    """
    Generate a security-focused error message for invalid port format inputs.
    
    This function creates user-friendly error messages that provide helpful guidance
    for entering valid port specifications while maintaining security best practices.
    
    Args:
        port_input (str): The invalid port input that was provided by the user
        
    Returns:
        dict: Structured error response with guidance for proper port formatting
        
    Security Features:
        - Only displays valid format examples
        - Excludes potentially harmful input patterns from error messages
        - Provides educational content without exposing attack vectors
    """
    return {
        'error': 'Invalid port format',
        'details': {
            'provided': port_input,
            'valid_formats': [
                'Single port: Gi1/0/24',
                'Port range: Gi1/0/1-5',
                'Multiple ports: Gi1/0/1,Gi1/0/5,Gi1/0/10',
                'Mixed format: Gi1/0/1-5,Te1/0/1,Tw1/0/2'
            ],
            'requirements': [
                'Use Dell interface naming: Gi (GigE), Te (10GigE), Tw (25GigE)',
                'Format: Interface[stack]/[module]/[port] (e.g., Gi1/0/24)',
                'Stack numbers: 1-8, Module: 0-3, Ports: 1-128',
                'Separate multiple entries with commas',
                'Use hyphens for port ranges within same interface type'
            ],
            'examples': {
                'correct': [
                    'Gi1/0/24',
                    'Gi1/0/1-5',
                    'Te1/0/1,Te1/0/3',
                    'Gi1/0/10-15,Gi2/0/20',
                    'Tw1/0/1,Tw1/0/2'
                ]
            }
        }
    }

def get_vlan_format_error_message(field_name, value):
    """
    Generate security-focused error messages for invalid VLAN-related inputs.
    
    Args:
        field_name (str): Name of the field that failed validation
        value (str): The invalid value that was provided
        
    Returns:
        dict: Structured error response with field-specific guidance
    """
    if field_name == 'vlan_id':
        return {
            'error': 'Invalid VLAN ID',
            'details': {
                'field': 'vlan_id',
                'provided': value,
                'valid_range': '1-4094 (IEEE 802.1Q standard)',
                'requirements': [
                    'Must be a numeric value',
                    'Range: 1 to 4094 (inclusive)',
                    'VLAN 0 and 4095 are reserved and not allowed'
                ],
                'examples': {
                    'correct': ['100', '200', '1500', '4000']
                }
            }
        }
    elif field_name == 'vlan_name':
        return {
            'error': 'Invalid VLAN name',
            'details': {
                'field': 'vlan_name',
                'provided': value,
                'requirements': [
                    'Must start with alphanumeric character',
                    'Can contain letters, numbers, hyphens, and underscores',
                    'Maximum length: 64 characters',
                    'Cannot be empty or reserved system names'
                ],
                'naming_standards': [
                    'Zone_Client_Name (recommended)',
                    'Internal_Network',
                    'Guest_Access', 
                    'IoT_Devices'
                ],
                'examples': {
                    'correct': [
                        'Zone_Client_ABC',
                        'Internal_Network',
                        'Guest_WiFi',
                        'IoT_Devices',
                        'Voice_VLAN'
                    ]
                }
            }
        }
    elif field_name == 'description':
        return {
            'error': 'Invalid port description',
            'details': {
                'field': 'description',
                'provided': value,
                'requirements': [
                    'Maximum length: 200 characters',
                    'Alphanumeric characters and safe punctuation only',
                    'No command injection characters allowed'
                ],
                'allowed_characters': 'Letters, numbers, spaces, hyphens, underscores, periods, commas, parentheses, brackets, hash, at-sign, plus, equals, colon',
                'examples': {
                    'correct': [
                        'Client Workstation - Room 101',
                        'Server Connection [Primary]',
                        'Access Point #3 - Floor 2',
                        'Printer Port (HP LaserJet)',
                        'Phone Port: Extension 1234'
                    ]
                }
            }
        }
    else:
        return {
            'error': f'Invalid {field_name}',
            'details': {
                'field': field_name,
                'provided': value,
                'message': 'Please check the format and try again'
            }
        }

# Dell Switch Model Port Configurations
SWITCH_PORT_CONFIG = {
    'N2000': {
        'interface_ports': 'Gi',  # GigabitEthernet interfaces
        'uplink_ports': 'Te',     # TenGigabitEthernet uplinks
        'max_interface_ports': 48,
        'uplink_port_range': '1/0/1-1/0/4'
    },
    'N3000': {
        'interface_ports': 'Gi',  # GigabitEthernet interfaces  
        'uplink_ports': 'Te',     # TenGigabitEthernet uplinks
        'max_interface_ports': 48,
        'uplink_port_range': '1/0/1-1/0/4'
    },
    'N3200': {
        'interface_ports': 'Te',  # TenGigabitEthernet interfaces
        'uplink_ports': 'Tw',     # TwentyFiveGigE uplinks
        'max_interface_ports': 48,
        'uplink_port_range': '1/0/1-1/0/4'
    }
}

class VLANManager:
    """Advanced VLAN Management with comprehensive safety checks."""
    
    def __init__(self, switch_ip, username, password, switch_model='N3000'):
        self.switch_ip = switch_ip
        self.username = username
        self.password = password
        self.switch_model = switch_model.upper()
        self.ssh_client = None
        
    def connect(self):
        """Establish SSH connection to switch with interactive shell."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=self.switch_ip,
                username=self.username,
                password=self.password,
                timeout=15
            )
            
            # Create interactive shell (like the main port tracer)
            self.shell = self.ssh_client.invoke_shell()
            time.sleep(2)
            
            # Clear initial output
            if self.shell.recv_ready():
                self.shell.recv(4096)
            
            logger.info(f"Successfully connected to switch {self.switch_ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to switch {self.switch_ip}: {str(e)}")
            return False
    
    def disconnect(self):
        """Close SSH connection."""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def execute_command(self, command, wait_time=1.0):
        """Execute command on switch via interactive shell and return output."""
        try:
            if not self.ssh_client or not hasattr(self, 'shell') or not self.shell:
                raise Exception("Not connected to switch or shell not initialized")
            
            # Check if shell is still active
            if self.shell.closed:
                logger.info(f"Shell closed, reconnecting to {self.switch_ip}")
                self.disconnect()
                if not self.connect():
                    raise Exception("Failed to reconnect to switch")
            
            # Send command via interactive shell (like main port tracer)
            self.shell.send(command + '\n')
            time.sleep(wait_time)
            
            # Collect output
            output = ""
            while self.shell.recv_ready():
                output += self.shell.recv(4096).decode('utf-8')
            
            # Try to get additional output with a bit more wait time
            time.sleep(0.5)
            while self.shell.recv_ready():
                output += self.shell.recv(4096).decode('utf-8')
            
            return output
            
        except OSError as e:
            if "Socket is closed" in str(e):
                logger.error(f"SSH connection to {self.switch_ip} was closed unexpectedly")
                raise Exception("SSH connection lost")
            else:
                raise
        except Exception as e:
            logger.error(f"Command execution failed on {self.switch_ip}: {str(e)}")
            raise
    
    def is_uplink_port(self, port_name):
        """Check if port is an uplink port based on switch model."""
        if self.switch_model not in SWITCH_PORT_CONFIG:
            # Default safety: treat Te and Tw ports as uplinks
            return port_name.startswith(('Te', 'Tw', 'Po'))
        
        config = SWITCH_PORT_CONFIG[self.switch_model]
        uplink_prefix = config['uplink_ports']
        
        # Port-channels are always considered uplinks
        if port_name.startswith('Po'):
            return True
            
        return port_name.startswith(uplink_prefix)
    
    def normalize_port_name(self, port_input):
        """Normalize port name to Dell switch format with multi-stack support."""
        port_input = port_input.strip()
        
        # Handle various input formats
        if '/' not in port_input and port_input.isdigit():
            # Just a number, assume Gi interface stack 1
            interface_prefix = SWITCH_PORT_CONFIG.get(self.switch_model, {}).get('interface_ports', 'Gi')
            return f"{interface_prefix}1/0/{port_input}"
        elif port_input.startswith(('gi', 'te', 'tw')):
            # Handle lowercase prefixes and multi-stack format
            lower_input = port_input.lower()
            
            if lower_input.startswith('gi'):
                # Handle formats like gi1, gi3, gi1/0/1, gi3/0/48
                remainder = port_input[2:]
                if remainder.isdigit():
                    # Format: gi1, gi2, gi3 (stack numbers)
                    stack_num = remainder
                    return f"Gi{stack_num}/0/1"  # Default to port 1
                elif '/' in remainder:
                    # Format: gi1/0/1, gi3/0/48
                    return f"Gi{remainder}"
                else:
                    return f"Gi{remainder}"
            elif lower_input.startswith('te'):
                # Handle formats like te1, te3, te1/0/1, te3/0/2
                remainder = port_input[2:]
                if remainder.isdigit():
                    # Format: te1, te2, te3 (stack numbers)
                    stack_num = remainder
                    return f"Te{stack_num}/0/1"  # Default to port 1
                elif '/' in remainder:
                    # Format: te1/0/1, te3/0/2
                    return f"Te{remainder}"
                else:
                    return f"Te{remainder}"
            elif lower_input.startswith('tw'):
                # Handle formats like tw1, tw3, tw1/0/1, tw3/0/2
                remainder = port_input[2:]
                if remainder.isdigit():
                    # Format: tw1, tw2, tw3 (stack numbers)
                    stack_num = remainder
                    return f"Tw{stack_num}/0/1"  # Default to port 1
                elif '/' in remainder:
                    # Format: tw1/0/1, tw3/0/2
                    return f"Tw{remainder}"
                else:
                    return f"Tw{remainder}"
            else:
                # Capitalize first letter and keep the rest
                port_input = port_input.capitalize()
        
        return port_input
    
    def parse_port_range(self, port_input):
        """Parse port input and return list of normalized port names."""
        ports = []
        
        # Split by comma for multiple ports/ranges
        for port_part in port_input.split(','):
            port_part = port_part.strip()
            
            # Handle ranges (e.g., "1-5", "Gi1/0/1-1/0/5")
            if '-' in port_part:
                if '/' in port_part:
                    # Full port name range (e.g., "Gi1/0/1-Gi1/0/5")
                    try:
                        start_port, end_port = port_part.split('-')
                        start_port = start_port.strip()
                        end_port = end_port.strip()
                        
                        # Extract port numbers
                        start_num = int(start_port.split('/')[-1])
                        end_num = int(end_port.split('/')[-1])
                        
                        # Generate range
                        prefix = '/'.join(start_port.split('/')[:-1])
                        for i in range(start_num, end_num + 1):
                            ports.append(f"{prefix}/{i}")
                    except:
                        logger.warning(f"Could not parse port range: {port_part}")
                        continue
                else:
                    # Simple number range (e.g., "1-5")
                    try:
                        start, end = map(int, port_part.split('-'))
                        interface_prefix = SWITCH_PORT_CONFIG.get(self.switch_model, {}).get('interface_ports', 'Gi')
                        for i in range(start, end + 1):
                            ports.append(f"{interface_prefix}1/0/{i}")
                    except:
                        logger.warning(f"Could not parse number range: {port_part}")
                        continue
            else:
                # Single port
                ports.append(self.normalize_port_name(port_part))
        
        return ports
    
    def get_vlan_info(self, vlan_id):
        """Check if VLAN exists and get its information with improved error handling."""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Try multiple command variations for Dell switches (N2048/N2000 compatible)
                logger.info(f"Switch model detected: '{self.switch_model}' - using appropriate commands")
                
                if self.switch_model.startswith('N2') or 'N2048' in self.switch_model.upper():
                    # Dell N2000 series (including N2048) - prioritize the working command
                    commands_to_try = [
                        f"show vlan id {vlan_id}",                        # N2000 series correct format (KNOWN TO WORK)
                        f"show running-config | include 'vlan {vlan_id}'", # Config-based search
                        f"show mac address-table vlan {vlan_id}",         # MAC table approach  
                        "show vlan",                                      # Standard VLAN command (may not work)
                    ]
                    logger.info(f"Using Dell N2000/N2048 series commands with authorization fallbacks on {self.switch_model}")
                else:
                    # Dell N3000+ series commands
                    commands_to_try = [
                        f"show vlan id {vlan_id}",        # N3000+ format
                        "show vlan brief",                # Get all VLANs and parse
                        "show vlan",                      # Alternative VLAN command
                        f"show vlan {vlan_id}"            # Some Dell models use this
                    ]
                    logger.info("Using Dell N3000+ series commands for VLAN check")
                
                output = None
                command_used = None
                
                for command in commands_to_try:
                    try:
                        output = self.execute_command(command)
                        command_used = command
                        if output and output.strip():  # Got some output
                            break
                    except Exception as cmd_e:
                        logger.debug(f"Command '{command}' failed: {str(cmd_e)}")
                        continue
                
                if not output:
                    raise Exception("All VLAN command variants failed")
                
                logger.info(f"VLAN {vlan_id} check using '{command_used}' (attempt {attempt + 1}): {output[:200]}...")
                
                logger.info(f"VLAN {vlan_id} check output (attempt {attempt + 1}): {output[:200]}...")  # Debug log
                
                # Parse VLAN information from Dell switch output
                vlan_exists = False
                vlan_name = "Unknown"
                
                # Check for common Dell switch VLAN output patterns
                if output and len(output.strip()) > 0:
                    lines = output.split('\n')
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Look for various VLAN output formats
                        # Dell N2048 Format: "123    LAN EZE CASTLE-VOICE             Po4,Gi1/0/5,   Static"
                        # Format 1: "123    VLAN_NAME    active    Gi1/0/1, Gi1/0/2"
                        # Format 2: "VLAN123   VLAN_NAME   active"
                        # Format 3: "VLAN Name: VLAN_NAME"
                        
                        # Check if line starts with the VLAN ID
                        if line.startswith(str(vlan_id)):
                            vlan_exists = True
                            parts = line.split()
                            if len(parts) >= 2:
                                # For Dell N2048, the name might be split across multiple words
                                # Extract everything between VLAN ID and the ports column
                                # Example: "123    LAN EZE CASTLE-VOICE             Po4,Gi1/0/5,   Static"
                                vlan_name_parts = []
                                for part in parts[1:]:
                                    # Stop when we hit ports (contains 'Gi', 'Te', 'Po') or 'Static'
                                    if any(port_prefix in part for port_prefix in ['Gi', 'Te', 'Po', 'Static']):
                                        break
                                    vlan_name_parts.append(part)
                                
                                if vlan_name_parts:
                                    vlan_name = ' '.join(vlan_name_parts)
                                else:
                                    vlan_name = parts[1] if len(parts) > 1 else "Unknown"
                            logger.info(f"VLAN {vlan_id} found: name='{vlan_name}'")
                            break
                        
                        # Check if line contains VLAN ID in first column/word
                        parts = line.split()
                        if len(parts) > 0 and parts[0] == str(vlan_id):
                            vlan_exists = True
                            if len(parts) >= 2:
                                # Same logic for name extraction
                                vlan_name_parts = []
                                for part in parts[1:]:
                                    if any(port_prefix in part for port_prefix in ['Gi', 'Te', 'Po', 'Static']):
                                        break
                                    vlan_name_parts.append(part)
                                
                                if vlan_name_parts:
                                    vlan_name = ' '.join(vlan_name_parts)
                                else:
                                    vlan_name = parts[1] if len(parts) > 1 else "Unknown"
                            logger.info(f"VLAN {vlan_id} found: name='{vlan_name}'")
                            break
                        
                        # Check for "VLAN Name:" pattern
                        if "VLAN Name:" in line or "Name:" in line:
                            # Extract name after the colon
                            if ":" in line:
                                name_part = line.split(":", 1)[1].strip()
                                if name_part:
                                    vlan_name = name_part
                                    vlan_exists = True
                                    logger.info(f"VLAN {vlan_id} found via name field: name='{vlan_name}'")
                                    break
                    
                    # If no specific pattern found, but we got output without error, check if it's a valid response
                    if not vlan_exists:
                        # Check if output contains authorization or permission errors
                        auth_errors = [
                            "Command Is Not Authorized", "Not Authorized", "Permission denied",
                            "Access denied", "Insufficient privileges"
                        ]
                        
                        # Check if output contains error messages indicating VLAN doesn't exist
                        error_indicators = [
                            "ERROR", "error", "Invalid", "invalid", 
                            "not found", "does not exist", "No such",
                            "VLAN does not exist", "Invalid VLAN"
                        ]
                        
                        has_auth_error = any(auth_err in output for auth_err in auth_errors)
                        has_error = any(indicator in output for indicator in error_indicators)
                        
                        if has_auth_error:
                            # User doesn't have privileges - assume VLAN might exist but can't verify
                            logger.warning(f"Authorization error checking VLAN {vlan_id}: {output[:100]}")
                            return {
                                'exists': False,  # Default to not existing for safety
                                'name': 'Unknown',
                                'id': vlan_id,
                                'error': 'Insufficient privileges to check VLAN existence',
                                'auth_error': True,
                                'raw_output': output[:500] if output else ""
                            }
                        elif not has_error and output.strip():
                            # We have output but no clear error - VLAN might exist
                            # This is a fallback for unusual output formats
                            vlan_exists = True
                            vlan_name = "Unknown"
                            logger.info(f"VLAN {vlan_id} assumed to exist based on non-error output")
                
                return {
                    'exists': vlan_exists,
                    'name': vlan_name,
                    'id': vlan_id,
                    'raw_output': output[:500] if output else ""  # Include raw output for debugging
                }
                
            except Exception as e:
                logger.warning(f"VLAN check attempt {attempt + 1} failed for VLAN {vlan_id}: {str(e)}")
                if attempt < max_retries - 1:
                    import time
                    logger.info(f"Retrying VLAN check in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"All attempts failed to check VLAN {vlan_id}: {str(e)}")
        
        # All attempts failed
        return {
            'exists': False, 
            'name': 'Unknown', 
            'id': vlan_id, 
            'error': f'Failed to check VLAN after {max_retries} attempts',
            'raw_output': ''
        }
    
    def create_vlan(self, vlan_id, vlan_name):
        """Create a new VLAN with specified ID and name."""
        try:
            commands = [
                "configure",
                f"vlan {vlan_id}",
                f"name \"{vlan_name}\"",
                "exit",
                "exit"
            ]
            
            for command in commands:
                self.execute_command(command)
            
            logger.info(f"Created VLAN {vlan_id} with name '{vlan_name}' on {self.switch_ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to create VLAN {vlan_id}: {str(e)}")
            return False
    
    def update_vlan_name(self, vlan_id, vlan_name):
        """Update existing VLAN name."""
        try:
            commands = [
                "configure",
                f"vlan {vlan_id}",
                f"name \"{vlan_name}\"",
                "exit",
                "exit"
            ]
            
            for command in commands:
                self.execute_command(command)
            
            logger.info(f"Updated VLAN {vlan_id} name to '{vlan_name}' on {self.switch_ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to update VLAN {vlan_id} name: {str(e)}")
            return False
    
    def get_port_status(self, port_name):
        """Get detailed port status including operational state and mode using faster commands."""
        try:
            # Try multiple port status commands for Dell N2048 compatibility
            status_commands = [
                f"show interface status {port_name}",     # Dell standard
                f"show interfaces status {port_name}",    # Alternative
                f"show interface {port_name}",            # Basic interface info
                f"show port {port_name}"                 # Some Dell models
            ]
            
            status_output = ""
            status_cmd_used = None
            
            for cmd in status_commands:
                try:
                    status_output = self.execute_command(cmd)
                    status_cmd_used = cmd
                    if status_output and status_output.strip() and "Invalid input" not in status_output:
                        break
                except Exception:
                    continue
            
            # Get port configuration (this is still needed for mode and VLAN info)
            config_commands = [
                f"show running-config interface {port_name}",
                f"show run interface {port_name}"
            ]
            
            config_output = ""
            for cmd in config_commands:
                try:
                    config_output = self.execute_command(cmd)
                    if config_output and config_output.strip() and "Invalid input" not in config_output:
                        break
                except Exception:
                    continue
            
            # Parse status from Dell 'show interface status' output
            # Format: "Gi1/0/24                  N/A    Unknown Auto Down    On    A  123"
            port_up = False
            port_mode = "access"  # Default assumption
            current_vlan = "1"    # Default VLAN
            
            # Parse the status output table format
            lines = status_output.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('-') or 'Port' in line:
                    continue
                    
                # Look for the port data line
                if port_name in line:
                    # Split by whitespace and parse columns
                    columns = line.split()
                    if len(columns) >= 8:  # Expected number of columns
                        # Column indices: 0=Port, 1=Description, 2=Duplex, 3=Speed, 4=Neg, 5=Link State, 6=Flow Ctrl, 7=M, 8=VLAN
                        try:
                            link_state = columns[5].lower()
                            port_up = link_state == 'up'
                            
                            # Get mode from column 7 (M)
                            mode_char = columns[7].upper()
                            if mode_char == 'A':
                                port_mode = 'access'
                            elif mode_char == 'T':
                                port_mode = 'trunk'
                            elif mode_char == 'G':
                                port_mode = 'general'
                            
                            # Get VLAN from column 8
                            if len(columns) >= 9:
                                current_vlan = columns[8]
                        except (IndexError, ValueError) as e:
                            logger.debug(f"Error parsing port status line '{line}': {str(e)}")
                            # Fall back to config parsing
                            pass
                    break
            
            # Also parse mode and VLAN from configuration as backup
            for line in config_output.split('\n'):
                line = line.strip().lower()
                if "switchport mode" in line:
                    if "trunk" in line:
                        port_mode = "trunk"
                    elif "general" in line:
                        port_mode = "general"
                    elif "access" in line:
                        port_mode = "access"
                elif "switchport access vlan" in line:
                    try:
                        config_vlan = line.split()[-1]
                        # Use config VLAN if status parsing didn't work
                        if current_vlan == "1" and config_vlan != "1":
                            current_vlan = config_vlan
                    except:
                        pass
            
            return {
                'port': port_name,
                'status': 'up' if port_up else 'down',
                'mode': port_mode,
                'current_vlan': current_vlan,
                'config_output': config_output
            }
        except Exception as e:
            logger.error(f"Failed to get port status for {port_name}: {str(e)}")
            return {
                'port': port_name,
                'status': 'unknown',
                'mode': 'unknown',
                'current_vlan': 'unknown',
                'config_output': ''
            }
    
    def change_port_vlan(self, port_name, vlan_id, description=None):
        """Change port VLAN assignment with description."""
        try:
            commands = [
                "configure",
                f"interface {port_name}",
                "switchport mode access",
                f"switchport access vlan {vlan_id}"
            ]
            
            if description:
                commands.insert(-1, f"description \"{description}\"")
            
            commands.extend(["exit", "exit"])
            
            for command in commands:
                self.execute_command(command)
            
            logger.info(f"Changed port {port_name} to VLAN {vlan_id} on {self.switch_ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to change port {port_name} VLAN: {str(e)}")
            return False
    
    def generate_interface_ranges(self, ports):
        """Generate interface range commands from a list of ports for batch configuration.
        
        This function optimizes VLAN configuration by grouping consecutive ports into ranges,
        which significantly improves performance on Dell switches that support interface range commands.
        
        TROUBLESHOOTING:
        - If ports aren't being grouped, check that port names follow Dell format (e.g., Gi1/0/24)
        - Look for "Could not parse port" warnings in logs for unsupported port formats
        - Ensure ports are on the same interface type (Gi, Te, Tw) and stack/slot
        
        Args:
            ports: List of port names (e.g., ['Gi1/0/1', 'Gi1/0/2', 'Gi1/0/5', 'Gi1/0/6', 'Gi1/0/7'])
            
        Returns:
            List of range strings (e.g., ['Gi1/0/1-2', 'Gi1/0/5-7'])
            Empty list if no ports can be parsed or grouped
            
        Example Output:
            Input:  ['Gi1/0/24', 'Gi1/0/25', 'Gi1/0/27']
            Output: ['Gi1/0/24-25', 'Gi1/0/27']
        """
        if not ports:
            return []
        
        # Group ports by interface type and stack
        port_groups = {}
        
        for port in ports:
            try:
                # Parse port name (e.g., 'Gi1/0/24' -> ['Gi1', '0', '24'])
                if '/' in port:
                    parts = port.split('/')
                    if len(parts) == 3:  # Standard format: Gi1/0/24
                        interface_stack = parts[0]  # 'Gi1'
                        slot = parts[1]  # '0'
                        port_num = int(parts[2])  # 24
                        
                        group_key = f"{interface_stack}/{slot}"  # 'Gi1/0'
                        if group_key not in port_groups:
                            port_groups[group_key] = []
                        port_groups[group_key].append(port_num)
                    elif len(parts) == 4:  # Some switches use 4-part format
                        interface_type = parts[0][:2]  # 'Gi'
                        stack = parts[0][2:]  # '1'
                        slot1 = parts[1]  # '0'
                        slot2 = parts[2]  # '0'
                        port_num = int(parts[3])  # 24
                        
                        group_key = f"{interface_type}{stack}/{slot1}/{slot2}"  # 'Gi1/0/0'
                        if group_key not in port_groups:
                            port_groups[group_key] = []
                        port_groups[group_key].append(port_num)
            except (ValueError, IndexError) as e:
                # If we can't parse it, treat as individual port
                logger.warning(f"Could not parse port {port} for range optimization: {str(e)}")
                continue
        
        # Generate ranges for each group
        ranges = []
        
        for group_key, port_nums in port_groups.items():
            if not port_nums:
                continue
                
            # Sort port numbers
            port_nums.sort()
            
            # Find consecutive ranges
            current_range_start = port_nums[0]
            current_range_end = port_nums[0]
            
            for i in range(1, len(port_nums)):
                if port_nums[i] == current_range_end + 1:
                    # Consecutive port, extend range
                    current_range_end = port_nums[i]
                else:
                    # Non-consecutive, finalize current range and start new one
                    if current_range_start == current_range_end:
                        ranges.append(f"{group_key}/{current_range_start}")
                    else:
                        ranges.append(f"{group_key}/{current_range_start}-{current_range_end}")
                    
                    current_range_start = port_nums[i]
                    current_range_end = port_nums[i]
            
            # Add the final range
            if current_range_start == current_range_end:
                ranges.append(f"{group_key}/{current_range_start}")
            else:
                ranges.append(f"{group_key}/{current_range_start}-{current_range_end}")
        
        return ranges
    
    def change_ports_vlan_batch(self, ports, vlan_id, description=None):
        """Change multiple ports VLAN assignment using interface range commands for efficiency.
        
        Args:
            ports: List of port names
            vlan_id: Target VLAN ID
            description: Port description (optional)
            
        Returns:
            dict: Results with success/failure details
        """
        if not ports:
            return {'success': False, 'message': 'No ports provided'}
        
        try:
            # Generate interface ranges for efficiency
            ranges = self.generate_interface_ranges(ports)
            logger.info(f"Generated interface ranges: {ranges} for ports: {ports}")
            
            results = {
                'success': True,
                'ports_changed': [],
                'ports_failed': [],
                'commands_executed': [],
                'ranges_used': ranges
            }
            
            # Process each range
            range_success = False
            for range_str in ranges:
                try:
                    commands = [
                        "configure",
                        f"interface range {range_str}",
                        "switchport mode access",
                        f"switchport access vlan {vlan_id}"
                    ]
                    
                    if description:
                        commands.insert(-1, f"description \"{description}\"")
                    
                    commands.extend(["exit", "exit"])
                    
                    # Execute commands for this range
                    range_output = ""
                    for command in commands:
                        output = self.execute_command(command)
                        range_output += output
                        results['commands_executed'].append(command)
                    
                    # Check if range command worked (look for errors)
                    if "Invalid" in range_output or "ERROR" in range_output or "error" in range_output:
                        logger.warning(f"Interface range command may have failed for {range_str}, output: {range_output[:200]}")
                        # Fallback: try individual ports
                        range_ports = self._extract_ports_from_range(range_str)
                        logger.info(f"Falling back to individual port configuration for: {range_ports}")
                        
                        for port in range_ports:
                            individual_success = self.change_port_vlan(port, vlan_id, description)
                            if individual_success:
                                results['ports_changed'].append(port)
                            else:
                                results['ports_failed'].append(port)
                    else:
                        # Range command appeared successful
                        range_ports = self._extract_ports_from_range(range_str)
                        results['ports_changed'].extend(range_ports)
                        range_success = True
                        logger.info(f"Successfully configured range {range_str} to VLAN {vlan_id} on {self.switch_ip}")
                    
                except Exception as e:
                    logger.error(f"Failed to configure range {range_str}: {str(e)}")
                    # Fallback: try individual ports
                    range_ports = self._extract_ports_from_range(range_str)
                    logger.info(f"Exception occurred, falling back to individual port configuration for: {range_ports}")
                    
                    for port in range_ports:
                        try:
                            individual_success = self.change_port_vlan(port, vlan_id, description)
                            if individual_success:
                                results['ports_changed'].append(port)
                            else:
                                results['ports_failed'].append(port)
                        except Exception as port_e:
                            logger.error(f"Failed to configure individual port {port}: {str(port_e)}")
                            results['ports_failed'].append(port)
            
            # If no ranges worked, try all ports individually as final fallback
            if not range_success and not results['ports_changed']:
                logger.warning("No interface ranges worked, trying all ports individually")
                results['ranges_used'] = []  # Clear ranges since they didn't work
                
                for port in ports:
                    try:
                        individual_success = self.change_port_vlan(port, vlan_id, description)
                        if individual_success:
                            results['ports_changed'].append(port)
                        else:
                            results['ports_failed'].append(port)
                    except Exception as port_e:
                        logger.error(f"Failed to configure individual port {port}: {str(port_e)}")
                        results['ports_failed'].append(port)
            
            # Update success status based on results
            results['success'] = len(results['ports_failed']) == 0 and len(results['ports_changed']) > 0
            
            logger.info(f"Batch operation complete: {len(results['ports_changed'])} changed, {len(results['ports_failed'])} failed")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to execute batch VLAN change: {str(e)}")
            return {
                'success': False,
                'message': f'Batch operation failed: {str(e)}',
                'ports_changed': [],
                'ports_failed': ports
            }
    
    def _extract_ports_from_range(self, range_str):
        """Extract individual port names from a range string.
        
        Args:
            range_str: Range string like 'Gi1/0/1-5' or 'Gi1/0/10'
            
        Returns:
            List of individual port names
        """
        ports = []
        
        try:
            if '-' in range_str:
                # Handle range like 'Gi1/0/1-5'
                base_part, range_part = range_str.rsplit('/', 1)
                if '-' in range_part:
                    start, end = map(int, range_part.split('-'))
                    for i in range(start, end + 1):
                        ports.append(f"{base_part}/{i}")
                else:
                    # Single port
                    ports.append(range_str)
            else:
                # Single port
                ports.append(range_str)
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Could not extract ports from range {range_str}: {str(e)}")
            ports.append(range_str)  # Fallback to original
        
        return ports

# Flask API Routes for VLAN Management

def vlan_change_workflow(switch_id, ports_input, description, vlan_id, vlan_name, force_change=False, skip_non_access=False):
    """
    Main VLAN change workflow with comprehensive safety checks.
    
    Args:
        switch_id: Database ID of the target switch
        ports_input: String containing ports (comma-separated, ranges supported)
        description: Description to set on interfaces
        vlan_id: Target VLAN ID
        vlan_name: VLAN name (for creation or update)
        force_change: If True, change all ports except uplinks (with confirmation)
        skip_non_access: If True, skip ports that are up or not in access mode
    
    Returns:
        dict: Workflow results with confirmations needed, changes made, and errors
    """
    
    # Get switch information from database
    try:
        switch = Switch.query.get(switch_id)
        if not switch:
            return {'error': 'Switch not found', 'status': 'error'}
        
        floor = Floor.query.get(switch.floor_id)
        site = Site.query.get(floor.site_id)
        
        switch_info = {
            'id': switch.id,
            'name': switch.name,
            'ip_address': switch.ip_address,
            'model': switch.model,
            'site_name': site.name,
            'floor_name': floor.name
        }
    except Exception as e:
        logger.error(f"Failed to get switch info: {str(e)}")
        return {'error': 'Database error', 'status': 'error'}
    
    # Initialize VLAN manager
    from port_tracer_web import SWITCH_USERNAME, SWITCH_PASSWORD
    vlan_manager = VLANManager(
        switch_info['ip_address'],
        SWITCH_USERNAME,
        SWITCH_PASSWORD,
        switch_info['model']
    )
    
    # Connect to switch
    if not vlan_manager.connect():
        return {'error': f'Could not connect to switch {switch_info["name"]}', 'status': 'error'}
    
    try:
        # Parse and validate ports
        ports = vlan_manager.parse_port_range(ports_input)
        if not ports:
            return {'error': 'No valid ports specified', 'status': 'error'}
        
        # Check for uplink ports (safety check)
        uplink_ports = [port for port in ports if vlan_manager.is_uplink_port(port)]
        if uplink_ports and not force_change:
            return {
                'status': 'confirmation_needed',
                'type': 'uplink_protection',
                'message': f'The following ports appear to be uplink ports: {", ".join(uplink_ports)}',
                'details': 'Uplink ports are protected from accidental changes. Use force change to override.',
                'uplink_ports': uplink_ports,
                'safe_ports': [port for port in ports if not vlan_manager.is_uplink_port(port)]
            }
        
        # Filter out uplink ports if force_change is not enabled
        if not force_change:
            original_ports = ports[:]
            ports = [port for port in ports if not vlan_manager.is_uplink_port(port)]
            if len(ports) != len(original_ports):
                logger.info(f"Filtered out {len(original_ports) - len(ports)} uplink ports")
        
        # Check VLAN existence
        vlan_info = vlan_manager.get_vlan_info(vlan_id)
        vlan_operation = None
        
        if vlan_info['exists']:
            if vlan_info['name'] != vlan_name:
                vlan_operation = 'update_name'
        else:
            vlan_operation = 'create'
        
        # Check port statuses
        port_statuses = []
        active_or_non_access_ports = []
        safe_ports = []
        ports_already_correct = []  # New: track ports already set to target VLAN
        
        for port in ports:
            status = vlan_manager.get_port_status(port)
            port_statuses.append(status)
            
            # Check if port is already configured with the target VLAN
            if status['current_vlan'] == str(vlan_id):
                ports_already_correct.append({
                    'port': port,
                    'reason': f'Port already assigned to VLAN {vlan_id}',
                    'current_status': status
                })
                logger.info(f"Port {port} already configured with target VLAN {vlan_id}, will be skipped")
                continue  # Skip further processing for this port
            
            # Check if port is active or not in access mode (up and/or not access mode)
            is_active_or_non_access = False
            if status['status'] == 'up' and status['mode'] != 'access':
                is_active_or_non_access = True
                active_or_non_access_ports.append({
                    'port': port,
                    'reason': 'Port is UP and not in ACCESS mode',
                    'current_status': status
                })
            elif status['status'] == 'up':
                is_active_or_non_access = True
                active_or_non_access_ports.append({
                    'port': port,
                    'reason': 'Port is UP',
                    'current_status': status
                })
            elif status['mode'] != 'access':
                is_active_or_non_access = True
                active_or_non_access_ports.append({
                    'port': port,
                    'reason': 'Port is not in ACCESS mode',
                    'current_status': status
                })
            
            if not is_active_or_non_access:
                safe_ports.append(port)
        
        # Handle active or non-access ports based on options
        if active_or_non_access_ports and not force_change and not skip_non_access:
            return {
                'status': 'confirmation_needed',
                'type': 'active_or_non_access_ports',
                'message': f'Found {len(active_or_non_access_ports)} active or non-access mode ports that need confirmation',
                'active_or_non_access_ports': active_or_non_access_ports,
                'safe_ports': safe_ports,
                'port_statuses': port_statuses,
                'vlan_operation': vlan_operation,
                'vlan_info': vlan_info
            }
        
        # Determine final ports to change
        final_ports = []
        skipped_ports = []
        
        # Add already correct ports to skipped list
        skipped_ports.extend([p['port'] for p in ports_already_correct])
        
        if skip_non_access:
            final_ports = safe_ports
            skipped_ports.extend([p['port'] for p in active_or_non_access_ports])
        elif force_change:
            # Still respect uplink protection even with force, and exclude already correct ports
            final_ports = [port for port in ports if not vlan_manager.is_uplink_port(port) and port not in skipped_ports]
        else:
            # Exclude already correct ports from final ports list
            final_ports = [port for port in ports if port not in skipped_ports]
        
        # Execute VLAN operation
        results = {
            'status': 'success',
            'switch_info': switch_info,
            'vlan_id': vlan_id,
            'vlan_name': vlan_name,
            'description': description,  # Include the description in results
            'total_ports_requested': len(ports),
            'ports_changed': [],
            'ports_failed': [],
            'ports_skipped': skipped_ports,
            'vlan_operation_result': None,
            'ranges_used': [],  # Initialize ranges_used
            'commands_executed': []  # Initialize commands_executed
        }
        
        # Handle VLAN creation/update
        if vlan_operation == 'create':
            if vlan_manager.create_vlan(vlan_id, vlan_name):
                results['vlan_operation_result'] = f'Created VLAN {vlan_id} with name "{vlan_name}"'
            else:
                results['vlan_operation_result'] = f'Failed to create VLAN {vlan_id}'
        elif vlan_operation == 'update_name':
            if vlan_manager.update_vlan_name(vlan_id, vlan_name):
                results['vlan_operation_result'] = f'Updated VLAN {vlan_id} name to "{vlan_name}"'
            else:
                results['vlan_operation_result'] = f'Failed to update VLAN {vlan_id} name'
        
        # Change port VLANs using batch processing with interface ranges
        if final_ports:
            try:
                batch_result = vlan_manager.change_ports_vlan_batch(final_ports, vlan_id, description)
                
                if batch_result['success']:
                    results['ports_changed'] = batch_result['ports_changed']
                    results['ports_failed'] = batch_result['ports_failed']
                    results['ranges_used'] = batch_result['ranges_used']
                    results['commands_executed'] = batch_result['commands_executed']
                    
                    # Log successful batch operation
                    ranges_str = ', '.join(batch_result['ranges_used'])
                    logger.info(f"Successfully configured {len(results['ports_changed'])} ports using ranges: {ranges_str}")
                else:
                    # Batch failed, add all to failed list
                    results['ports_failed'].extend(final_ports)
                    logger.error(f"Batch VLAN change failed: {batch_result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                # Exception in batch processing, add all to failed list
                results['ports_failed'].extend(final_ports)
                logger.error(f"Exception in batch VLAN processing: {str(e)}")
        
        # Summary
        results['summary'] = {
            'total_requested': len(ports),
            'changed': len(results['ports_changed']),
            'failed': len(results['ports_failed']),
            'skipped': len(results['ports_skipped']),
            'already_correct': len(ports_already_correct),
            'uplink_protected': len([p for p in ports if vlan_manager.is_uplink_port(p)])
        }
        
        # Enhanced success message with ranges and description
        if results['ports_changed']:
            success_parts = []
            
            # VLAN assignment info
            success_parts.append(f"Successfully changed {len(results['ports_changed'])} ports to VLAN {vlan_id} ({vlan_name})")
            
            # Interface ranges used for efficiency
            if results['ranges_used']:
                ranges_str = ', '.join(results['ranges_used'])
                success_parts.append(f"Interface ranges configured: {ranges_str}")
            
            # Description applied
            if description and description.strip():
                success_parts.append(f"Port description applied: \"{description}\"")
            
            # VLAN operation performed
            if results['vlan_operation_result']:
                success_parts.append(results['vlan_operation_result'])
                
            # Add information about skipped ports that were already correct
            if ports_already_correct:
                already_correct_count = len(ports_already_correct)
                already_correct_ports = [p['port'] for p in ports_already_correct]
                port_list = ', '.join(already_correct_ports[:5])
                if len(already_correct_ports) > 5:
                    port_list += f" and {len(already_correct_ports) - 5} more"
                success_parts.append(f"Skipped {already_correct_count} ports already assigned to VLAN {vlan_id}: {port_list}")
            
            results['success_message'] = '\n'.join(success_parts)
        else:
            results['success_message'] = "No ports were changed."
        
        return results
        
    finally:
        vlan_manager.disconnect()

# New API endpoint - this would be added to port_tracer_web.py

def add_vlan_management_routes(app):
    """Add VLAN management routes to Flask app."""
    
    @app.route('/api/vlan/change', methods=['POST'])
    def api_change_port_vlan():
        """API endpoint for advanced VLAN change workflow."""
        if 'username' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_role = session.get('role', 'oss')
        if user_role not in ['netadmin', 'superadmin']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        try:
            data = request.json
            username = session['username']
            
            # Required fields
            required_fields = ['switch_id', 'ports', 'vlan_id', 'vlan_name']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Optional fields
            description = data.get('description', '')
            force_change = data.get('force_change', False)
            skip_problematic = data.get('skip_problematic', False)
            
            # Execute workflow
            result = vlan_change_workflow(
                switch_id=data['switch_id'],
                ports_input=data['ports'],
                description=description,
                vlan_id=data['vlan_id'],
                vlan_name=data['vlan_name'],
                force_change=force_change,
                skip_problematic=skip_problematic
            )
            
            # Log the operation
            from port_tracer_web import audit_logger
            if result['status'] == 'success':
                audit_logger.info(f"User: {username} - VLAN CHANGE - Switch: {result.get('switch_info', {}).get('name', 'unknown')}, VLAN: {data['vlan_id']}, Ports: {data['ports']}")
            else:
                audit_logger.warning(f"User: {username} - VLAN CHANGE FAILED - Switch ID: {data['switch_id']}, Error: {result.get('error', 'unknown')}")
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"VLAN change API error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/vlan/check', methods=['POST'])
    def api_check_vlan():
        """Check VLAN existence on switch."""
        if 'username' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_role = session.get('role', 'oss')
        if user_role not in ['netadmin', 'superadmin']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        try:
            data = request.json
            switch_id = data.get('switch_id')
            vlan_id = data.get('vlan_id')
            
            if not all([switch_id, vlan_id]):
                return jsonify({'error': 'Missing switch_id or vlan_id'}), 400
            
            # Get switch info
            switch = Switch.query.get(switch_id)
            if not switch:
                return jsonify({'error': 'Switch not found'}), 404
            
            # Initialize VLAN manager
            from port_tracer_web import SWITCH_USERNAME, SWITCH_PASSWORD
            vlan_manager = VLANManager(
                switch.ip_address,
                SWITCH_USERNAME,
                SWITCH_PASSWORD,
                switch.model
            )
            
            if not vlan_manager.connect():
                return jsonify({'error': 'Could not connect to switch'}), 500
            
            try:
                vlan_info = vlan_manager.get_vlan_info(vlan_id)
                return jsonify(vlan_info)
            finally:
                vlan_manager.disconnect()
                
        except Exception as e:
            logger.error(f"VLAN check API error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/api/port/status', methods=['POST'])
    def api_check_port_status():
        """Check port status on switch."""
        if 'username' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_role = session.get('role', 'oss')
        if user_role not in ['netadmin', 'superadmin']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        try:
            data = request.json
            switch_id = data.get('switch_id')
            ports_input = data.get('ports')
            
            if not all([switch_id, ports_input]):
                return jsonify({'error': 'Missing switch_id or ports'}), 400
            
            # Get switch info
            switch = Switch.query.get(switch_id)
            if not switch:
                return jsonify({'error': 'Switch not found'}), 404
            
            # Initialize VLAN manager
            from port_tracer_web import SWITCH_USERNAME, SWITCH_PASSWORD
            vlan_manager = VLANManager(
                switch.ip_address,
                SWITCH_USERNAME,
                SWITCH_PASSWORD,
                switch.model
            )
            
            if not vlan_manager.connect():
                return jsonify({'error': 'Could not connect to switch'}), 500
            
            try:
                # Parse ports
                ports = vlan_manager.parse_port_range(ports_input)
                port_statuses = []
                
                for port in ports:
                    status = vlan_manager.get_port_status(port)
                    status['is_uplink'] = vlan_manager.is_uplink_port(port)
                    port_statuses.append(status)
                
                return jsonify({
                    'ports': port_statuses,
                    'switch_model': switch.model
                })
            finally:
                vlan_manager.disconnect()
                
        except Exception as e:
            logger.error(f"Port status API error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

if __name__ == "__main__":
    # Test the VLAN manager functionality
    pass
