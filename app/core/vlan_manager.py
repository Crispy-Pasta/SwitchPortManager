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

NEW ENHANCED FEATURES (v2.1.5):
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
VERSION: 2.1.5 (Enhanced VLAN Management with Session Timeout Improvements)
LAST UPDATED: 2025-08-07
COMPATIBILITY: Python 3.7+, Dell PowerConnect N-Series Switches
"""

import paramiko
import logging
import re
import time
from datetime import datetime
from flask import Flask, jsonify, request, session
from app.core.database import db, Switch, Site, Floor
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
                logger.debug(f"Port validation failed: Invalid start port '{start_port}' in range '{part}'")
                return False
            
            # End port can be:
            # 1. Just a number for shorthand notation (Gi1/0/1-5)
            # 2. Full port specification (Gi1/0/1-Gi1/0/5 or gi1/0/1-gi1/0/5)
            if not _is_valid_single_port(end_port) and not _is_valid_port_number(end_port):
                logger.debug(f"Port validation failed: Invalid end port '{end_port}' in range '{part}'")
                return False
        else:
            # Single port validation
            if not _is_valid_single_port(part):
                return False
    
    return True

def _is_valid_single_port(port):
    """Validate a single port specification."""
    # Dell switch port format: Interface[stack]/[module]/[port]
    # Examples: Gi1/0/24, Te1/0/1, Tw1/0/1, gi1/0/24, te1/0/1, tw1/0/1
    pattern = re.compile(r'^(Gi|gi|Te|te|Tw|tw)(\d{1,2})/(\d{1,2})/(\d{1,3})$', re.IGNORECASE)
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
            
            # Try to disable terminal pagination and widen width to avoid wrapping
            # Different Dell NOS variants accept different commands; we try several safely.
            try:
                init_cmds = [
                    "terminal length 0",   # Common on many NOS
                    "console length 0",    # Dell N-Series OS 6.x
                    "terminal width 511",  # Max width to reduce line wraps
                ]
                for c in init_cmds:
                    try:
                        self.shell.send(c + '\n')
                        time.sleep(0.2)
                        # Drain any response without logging noise
                        while self.shell.recv_ready():
                            _ = self.shell.recv(4096)
                    except Exception:
                        # Ignore if a particular init command is not supported
                        pass
                logger.info("Terminal pagination disabled (length 0) and width set (where supported)")
            except Exception:
                # Non-fatal: if this fails, adaptive reading below will still try to cope
                logger.warning("Failed to run terminal init commands; proceeding with adaptive reads")
            
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
    
    def execute_command(self, command, wait_time=1.0, expect_large_output=False):
        """Execute command on switch via interactive shell and return output.
        
        Args:
            command: Command to execute
            wait_time: Initial wait time after sending command
            expect_large_output: If True, use extended collection for commands that might have paginated output
        """
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
            
            # Adaptive output collection loop with increased timeouts for reliability
            output = ""
            start_time = time.time()
            last_data_time = start_time
            idle_timeout = 2.5 if expect_large_output else 1.5   # Increased from 1.2/0.5 to 2.5/1.5
            max_duration = 30.0 if expect_large_output else 15.0  # Increased from 10.0/3.0 to 30.0/15.0
            pagination_prompts = ["--More--", "Press any key to continue", "<space> to continue"]
            
            while True:
                read_any = False
                while self.shell.recv_ready():
                    chunk = self.shell.recv(65535).decode('utf-8', errors='ignore')
                    if not chunk:
                        break
                    output += chunk
                    read_any = True
                    last_data_time = time.time()
                    
                    # Handle pagination prompts if terminal length wasn't honored
                    if any(p in chunk for p in pagination_prompts):
                        try:
                            self.shell.send(' ')
                        except Exception:
                            pass
                    
                if not read_any:
                    # No data available at the moment; brief sleep
                    time.sleep(0.1)
                
                now = time.time()
                if (now - last_data_time) > idle_timeout:
                    break
                if (now - start_time) > max_duration:
                    logger.debug("Max duration reached for command output collection")
                    break
            
            # Final small drain
            time.sleep(0.2)
            while self.shell.recv_ready():
                output += self.shell.recv(65535).decode('utf-8', errors='ignore')
            
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
            
                    # Retrieved port status and configuration data
            
            # Parse status from Dell switch output - Enhanced parsing logic
            port_up = False
            port_mode = "access"  # Default assumption
            current_vlan = "1"    # Default VLAN
            
            # Enhanced parsing for Dell switch status output
            # Multiple possible formats:
            # Format 1: "Gi1/0/24    N/A    Unknown    Auto    Down    On    A    123"
            # Format 2: "gi1/0/24    connected    1000    full    a-1000    123"
            # Format 3: "Port    Type    Duplex    Speed    Neg    Link    State    VLAN"
            
            lines = status_output.split('\n')
            for line_idx, line in enumerate(lines):
                original_line = line
                line = line.strip()
                if not line:
                    continue
                    
                # Skip command echoes (lines that start with "show" commands)
                if line.lower().startswith(('show ', 'console', 'enable', 'configure')):
                    continue
                    
                # Skip header lines and separators
                if any(header in line.lower() for header in ['port', 'name', 'type', 'duplex', 'speed', 'link', 'state', 'vlan']) and line_idx < 10:
                    continue
                if line.startswith('-') or line.startswith('='):
                    continue
                    
                # Look for the port data line - be more flexible with port name matching
                port_name_variations = [
                    port_name,
                    port_name.lower(),
                    port_name.upper()
                ]
                
                line_contains_port = False
                # Only check for port name if this doesn't look like a command or header
                if not any(cmd in line.lower() for cmd in ['show', 'interface', 'status', 'configure', 'enable']):
                    for port_variation in port_name_variations:
                        if port_variation in line.lower():
                            line_contains_port = True
                            break
                
                if line_contains_port:
                    logger.info(f"Found port data line for {port_name} at line {line_idx}: '{original_line}'")
                    
                    # Split by multiple whitespace to handle variable spacing
                    import re
                    columns = re.split(r'\s{2,}|\t', line)  # Split on 2+ spaces or tabs
                    if len(columns) < 3:  # If that doesn't work, try single space
                        columns = line.split()
                    
                    # Parse status output columns
                    
                    if len(columns) >= 3:  # Minimum expected columns
                        # Enhanced link state detection for Dell switch format:
                        # Expected format: "Gi3/0/25  JP PC           Full   1000    Auto Up      On    A  1"
                        # Columns: Port, Description, Duplex, Speed, Neg, Link_State, Flow_Ctrl, Mode, VLAN
                        
                        link_state_found = False
                        
                        # Method 1: Look for explicit "Up" or "Down" in Link State column
                        # Also check for common Dell patterns like "Auto Up", "Auto Down", etc.
                        for i, col in enumerate(columns):
                            col_stripped = col.strip()
                            col_lower = col_stripped.lower()
                            
                            # Direct link state indicators (most reliable)
                            if col_lower in ['up', 'connected']:
                                port_up = True
                                link_state_found = True
                                logger.info(f"Found explicit UP state: '{col_stripped}'")
                                break
                            elif col_lower in ['down', 'notconnect', 'nolink', 'disabled']:
                                port_up = False
                                link_state_found = True
                                logger.info(f"Found explicit DOWN state: '{col_stripped}'")
                                break
                        
                        # Method 1.5: Look for compound indicators like "Auto Up", "Auto Down"
                        if not link_state_found:
                            line_words = original_line.split()
                            for i in range(len(line_words) - 1):
                                if line_words[i].lower() == 'auto' and i + 1 < len(line_words):
                                    next_word = line_words[i + 1].lower()
                                    if next_word == 'up':
                                        port_up = True
                                        link_state_found = True
                                        logger.info(f"Found compound UP state: '{line_words[i]} {line_words[i + 1]}'")
                                        break
                                    elif next_word in ['down', 'notconnect']:
                                        port_up = False
                                        link_state_found = True
                                        logger.info(f"Found compound DOWN state: '{line_words[i]} {line_words[i + 1]}'")
                                        break
                        
                        # Method 2: If no explicit state found, look for speed + duplex combination
                        if not link_state_found:
                            has_speed = False
                            has_duplex = False
                            has_down_indicator = False
                            
                            for i, col in enumerate(columns):
                                col_stripped = col.strip()
                                col_lower = col_stripped.lower()
                                
                                # Check for speed indicators
                                if re.match(r'^(10|100|1000|10000)$', col_stripped):
                                    has_speed = True
                                
                                # Check for duplex indicators
                                elif col_lower in ['full', 'half']:
                                    has_duplex = True
                                
                                # Check for down indicators
                                elif col_lower in ['down', 'notconnect', 'disabled', 'err-disabled']:
                                    has_down_indicator = True
                            
                            # If we have both speed and duplex without down indicators, assume UP
                            if (has_speed or has_duplex) and not has_down_indicator:
                                port_up = True
                                link_state_found = True
                            elif has_down_indicator:
                                port_up = False
                                link_state_found = True
                        
                        # Method 3: Parse the exact Dell format if we can identify column positions
                        if not link_state_found:
                            # Try to parse based on known Dell switch output format
                            # "Gi3/0/25  JP PC           Full   1000    Auto Up      On    A  1"
                            # Look for "Up" or "Down" that appears after speed/duplex info
                            
                            line_words = original_line.split()
                            
                            # Look for Up/Down in the word list
                            for i, word in enumerate(line_words):
                                word_lower = word.lower().strip()
                                if word_lower == 'up':
                                    port_up = True
                                    link_state_found = True
                                    break
                                elif word_lower in ['down', 'notconnect']:
                                    port_up = False
                                    link_state_found = True
                                    break
                        
                        # Method 4: Final fallback - safer heuristic analysis
                        if not link_state_found:
                            line_content = original_line.lower()
                            
                            # Be more precise: look for UP/DOWN in likely positions
                            if ' up ' in line_content or line_content.endswith(' up'):
                                port_up = True
                                logger.info(f"Found UP via text search in: '{original_line[:50]}...'")
                            elif any(down_word in line_content for down_word in [' down ', ' notconnect', ' disabled']):
                                port_up = False
                                logger.info(f"Found DOWN via text search in: '{original_line[:50]}...'")
                            else:
                                # CRITICAL FIX: Default to DOWN when status is unclear
                                # This prevents false positives where ports appear UP when they're DOWN
                                port_up = False
                                logger.warning(f"Port {port_name} status unclear from: '{original_line[:50]}...', defaulting to DOWN for safety")
                        
                        # Look for mode indicator (A=Access, T=Trunk, G=General)
                        for i, col in enumerate(columns):
                            col_upper = col.upper().strip()
                            if col_upper in ['A', 'T', 'G']:
                                mode_char = col_upper
                                if mode_char == 'A':
                                    port_mode = 'access'
                                elif mode_char == 'T':
                                    port_mode = 'trunk'
                                elif mode_char == 'G':
                                    port_mode = 'general'
                                break
                        
                        # Look for VLAN ID - handle General mode format first
                        vlan_found = False
                        
                        # First pass: Look for General mode VLAN format "(1),20,203,1120,1124,1131"
                        for i, col in enumerate(columns):
                            col_stripped = col.strip()
                            if '(' in col_stripped:
                                # Extract native VLAN ID from general mode format (native VLAN is in parentheses)
                                vlan_match = re.search(r'\((\d+)\)', col_stripped)
                                if vlan_match:
                                    current_vlan = vlan_match.group(1)
                                    vlan_found = True
                                    # If we find general mode format, set the mode to general
                                    port_mode = 'general'
                                    logger.info(f"Found General mode native VLAN '{current_vlan}' from '{col_stripped}'")
                                    break
                        
                        # Second pass: If no General mode format found, look for simple numeric VLAN
                        if not vlan_found:
                            for i in range(len(columns) - 1, -1, -1):  # Search backwards from end
                                col = columns[i].strip()
                                if col.isdigit():
                                    vlan_candidate = int(col)
                                    if 1 <= vlan_candidate <= 4094:
                                        current_vlan = col
                                        break
                    else:
                        logger.warning(f"Insufficient columns ({len(columns)}) in status line: {line}")
                    
                    break  # Found the port line, stop searching
            
            # Also parse mode and VLAN from configuration as backup/verification
            if config_output:
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
                            # Only use config VLAN if status parsing didn't find one AND port is not in general mode
                            # For general mode ports, the status shows the native VLAN correctly in parentheses
                            if current_vlan == "1" and config_vlan != "1" and config_vlan.isdigit() and port_mode != "general":
                                current_vlan = config_vlan
                        except:
                            pass
            
            result = {
                'port': port_name,
                'status': 'up' if port_up else 'down',
                'mode': port_mode,
                'current_vlan': current_vlan,
                'config_output': config_output[:300] + '...' if len(config_output) > 300 else config_output,
                'raw_status_output': status_output[:500] + '...' if len(status_output) > 500 else status_output  # Include for debugging
            }
            
            logger.info(f"Port {port_name} final status: {result['status']}, mode: {result['mode']}, VLAN: {result['current_vlan']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get port status for {port_name}: {str(e)}")
            return {
                'port': port_name,
                'status': 'unknown',
                'mode': 'unknown',
                'current_vlan': 'unknown',
                'config_output': '',
                'error': str(e)
            }
    
    def get_bulk_port_status(self, ports):
        """
        Get status for multiple ports using a single 'show interfaces status' command.
        This is much more efficient than calling get_port_status() for each port individually.
        
        Args:
            ports: List of port names to check
            
        Returns:
            dict: Dictionary with port names as keys and status info as values
        """
        if not ports:
            return {}
        
        port_statuses = {}
        
        try:
            # Get all interface statuses with a single command
            status_commands = [
                "show interfaces status | no-more",  # If supported, prevents paging
                "show interfaces status",            # Dell standard
                "show interface status",             # Alternative
                "show ports status",                 # Some Dell models
            ]
            
            status_output = ""
            status_cmd_used = None
            
            for cmd in status_commands:
                try:
                    # Use enhanced collection for bulk status commands that may have large output
                    status_output = self.execute_command(cmd, wait_time=1.5, expect_large_output=True)
                    status_cmd_used = cmd
                    if status_output and status_output.strip() and "Invalid input" not in status_output:
                        break
                except Exception:
                    continue
            
            if not status_output:
                logger.error("No valid status output obtained from bulk status commands")
                return {port: {'error': 'No status output available'} for port in ports}
            
            logger.info(f"Bulk status command '{status_cmd_used}' collected {len(status_output)} chars from switch")
            
            # Parse the bulk status output
            lines = status_output.split('\n')
            header_found = False
            
            # Create a set of requested ports for quick lookup (case-insensitive)
            requested_ports = set()
            for port in ports:
                requested_ports.add(port.lower())
            
            logger.info(f"Parsing {len(lines)} lines of bulk status output for {len(ports)} requested ports")
            
            for line_idx, line in enumerate(lines):
                original_line = line
                line = line.strip()
                
                if not line:
                    continue
                
                # Skip command echoes
                if line.lower().startswith(('show ', 'console', 'enable', 'configure')):
                    continue
                
                # Look for header line to confirm we have the right format
                if any(header in line.lower() for header in ['port', 'duplex', 'speed', 'link', 'state', 'vlan']) and not header_found:
                    header_found = True
                    logger.info(f"Found status output header at line {line_idx}")
                    continue
                
                # Skip separator lines
                if line.startswith('-') or line.startswith('='):
                    continue
                
                # Parse port data lines
                if header_found and line and not line.lower().startswith(('port', 'show')):
                    port_info = self._parse_bulk_status_line(original_line)
                    
                    if port_info:
                        if port_info['port'].lower() in requested_ports:
                            port_statuses[port_info['port']] = port_info
                            logger.info(f"Found {port_info['port']}: {port_info['status']}, {port_info['mode']}, VLAN {port_info['current_vlan']}")
            
            # For any requested ports not found in bulk output, use individual port status calls
            logger.info(f"Found {len(port_statuses)} ports in bulk output, checking for missing ports...")
            missing_ports = []
            for port in ports:
                port_found = False
                # Try exact match first
                if port in port_statuses:
                    port_found = True
                # Try case-insensitive match
                elif not port_found:
                    for parsed_port in port_statuses.keys():
                        if parsed_port.lower() == port.lower():
                            port_found = True
                            # Copy to exact requested port name for consistency
                            if port != parsed_port:
                                port_statuses[port] = port_statuses[parsed_port]
                            break
                
                if not port_found:
                    missing_ports.append(port)
                    logger.warning(f"× Port {port} not found in bulk status output")
            
            # Call individual port status for missing ports
            if missing_ports:
                logger.info(f"Calling individual port status for {len(missing_ports)} missing ports: {missing_ports}")
                for port in missing_ports:
                    try:
                        individual_status = self.get_port_status(port)
                        port_statuses[port] = individual_status
                        logger.info(f"[FALLBACK] Individual port status for {port}: {individual_status['status']}, {individual_status['mode']}, VLAN {individual_status['current_vlan']}")
                    except Exception as port_e:
                        logger.error(f"Failed to get individual status for port {port}: {str(port_e)}")
                        port_statuses[port] = {
                            'port': port,
                            'status': 'unknown',
                            'mode': 'unknown',
                            'current_vlan': 'unknown',
                            'error': f'Individual port status failed: {str(port_e)}'
                        }
            
            logger.info(f"Bulk port status retrieved for {len(port_statuses)} ports using single command")
            return port_statuses
            
        except Exception as e:
            logger.error(f"Failed to get bulk port status: {str(e)}")
            # Fallback to individual port checks
            logger.info("Falling back to individual port status checks")
            for port in ports:
                try:
                    port_statuses[port] = self.get_port_status(port)
                except Exception as port_e:
                    logger.error(f"Failed to get status for port {port}: {str(port_e)}")
                    port_statuses[port] = {
                        'port': port,
                        'status': 'unknown',
                        'mode': 'unknown',
                        'current_vlan': 'unknown',
                        'error': str(port_e)
                    }
            
            return port_statuses
    
    def _parse_bulk_status_line(self, line):
        """
        Parse a single line from 'show interfaces status' output.
        
        Expected format: "Gi1/0/1  Description  Full  1000  Auto  Up  On  A  123"
        
        Args:
            line: Single line from status output
            
        Returns:
            dict: Port information or None if line couldn't be parsed
        """
        try:
            line = line.strip()
            if not line:
                return None
            
            # Split by multiple whitespace or tabs to handle variable spacing
            import re
            columns = re.split(r'\s{2,}|\t', line)
            if len(columns) < 3:  # Fallback to single space
                columns = line.split()
            
            if len(columns) < 3:
                return None
            
            # Extract port name (first column)
            port_name = columns[0].strip()
            if not port_name or not re.match(r'^(Gi|gi|Te|te|Tw|tw|Po|po)\d', port_name):
                return None
            
            # Initialize defaults
            port_up = False
            port_mode = "access"
            current_vlan = "1"
            description = ""
            
            # Extract description if present (second column, might be empty)
            if len(columns) > 1:
                description = columns[1].strip()
            
            # Parse status information from remaining columns
            link_state_found = False
            general_vlan_found = False  # Track if we found a General mode VLAN
            
            for i, col in enumerate(columns):
                col_stripped = col.strip()
                col_lower = col_stripped.lower()
                
                # Look for link state
                if col_lower in ['up', 'connected'] and not link_state_found:
                    port_up = True
                    link_state_found = True
                elif col_lower in ['down', 'notconnect', 'disabled', 'disable'] and not link_state_found:
                    port_up = False
                    link_state_found = True
                
                # Look for mode indicator (A=Access, T=Trunk, G=General)
                elif col_stripped.upper() in ['A', 'T', 'G']:
                    mode_char = col_stripped.upper()
                    if mode_char == 'A':
                        port_mode = 'access'
                    elif mode_char == 'T':
                        port_mode = 'trunk'
                    elif mode_char == 'G':
                        port_mode = 'general'
                
                # Handle General mode VLAN format first: "(1),20,203,1120,1124,1131"
                elif '(' in col_stripped:
                    # Extract native VLAN ID from general mode format (native VLAN is in parentheses)
                    vlan_match = re.search(r'\((\d+)\)', col_stripped)
                    if vlan_match:
                        current_vlan = vlan_match.group(1)
                        general_vlan_found = True  # Mark that we found a General mode VLAN
                        # If we find general mode format, set the mode to general
                        port_mode = 'general'
                
                # Look for VLAN ID (numeric values, usually at the end) - but only if not already found in general format
                elif col_stripped.isdigit() and not general_vlan_found:
                    vlan_candidate = int(col_stripped)
                    if 1 <= vlan_candidate <= 4094:
                        current_vlan = col_stripped
            
            # Heuristic fallback for link state if not explicitly found
            if not link_state_found:
                # CRITICAL FIX: Look for "Down", "notconnect", etc. in the text first
                line_content = line.lower()
                
                # Check for UP indicators (be precise about positioning)
                if ' up ' in line_content or line_content.endswith(' up'):
                    port_up = True
                # Check for DOWN indicators (broader search as these can appear in various forms)
                elif any(down_indicator in line_content for down_indicator in 
                        [' down ', ' notconnect', ' disabled', ' nolink', 'err-disabled']):
                    port_up = False
                else:
                    # REMOVED THE BUGGY HEURISTIC: Don't assume UP based on speed/duplex
                    # Dell switches show speed/duplex even for DOWN ports!
                    # Always default to DOWN when status is unclear for safety
                    port_up = False
                    logger.warning(f"Port {port_name} status unclear from bulk parse, defaulting to DOWN for safety")
            
            return {
                'port': port_name,
                'status': 'up' if port_up else 'down',
                'mode': port_mode,
                'current_vlan': current_vlan,
                'description': description,
                'raw_line': line
            }
            
        except Exception as e:
            logger.debug(f"Failed to parse bulk status line '{line}': {str(e)}")
            return None
    
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
                    
                    # Enhanced success/failure detection for range commands
                    range_failed = False
                    if "Invalid" in range_output or "ERROR" in range_output or "error" in range_output:
                        logger.warning(f"Interface range command failed for {range_str}, output: {range_output[:200]}")
                        range_failed = True
                    
                    # Extract ports from range for individual verification
                    range_ports = self._extract_ports_from_range(range_str)
                    
                    if range_failed:
                        # Fallback: try individual ports and verify each one
                        logger.info(f"Falling back to individual port configuration for: {range_ports}")
                        
                        for port in range_ports:
                            # Try to configure individual port
                            individual_success = self.change_port_vlan(port, vlan_id, description)
                            if individual_success:
                                # Double-check: verify the port was actually changed
                                verification_status = self.get_port_status(port)
                                if verification_status['current_vlan'] == str(vlan_id):
                                    results['ports_changed'].append(port)
                                    logger.info(f"Successfully changed and verified port {port} to VLAN {vlan_id}")
                                else:
                                    results['ports_failed'].append(port)
                                    logger.error(f"Port {port} configuration appeared successful but verification failed - expected VLAN {vlan_id}, got {verification_status['current_vlan']}")
                            else:
                                results['ports_failed'].append(port)
                                logger.error(f"Failed to configure individual port {port}")
                    else:
                        # Range command appeared successful - verify each port in the range
                        logger.info(f"Range command succeeded for {range_str}, verifying individual ports: {range_ports}")
                        range_success = True
                        
                        # Verify each port in the range was actually changed
                        for port in range_ports:
                            try:
                                # Give the switch a moment to process the change
                                time.sleep(0.1)
                                verification_status = self.get_port_status(port)
                                if verification_status['current_vlan'] == str(vlan_id):
                                    results['ports_changed'].append(port)
                                    logger.debug(f"Verified port {port} successfully changed to VLAN {vlan_id}")
                                else:
                                    results['ports_failed'].append(port)
                                    logger.error(f"Port {port} range configuration failed - expected VLAN {vlan_id}, got {verification_status['current_vlan']}")
                            except Exception as verify_e:
                                logger.warning(f"Could not verify port {port} status after range config: {str(verify_e)}")
                                # If we can't verify, assume it worked since the range command succeeded
                                results['ports_changed'].append(port)
                        
                        logger.info(f"Range {range_str} verification complete: {len([p for p in range_ports if p in results['ports_changed']])} changed, {len([p for p in range_ports if p in results['ports_failed']])} failed")
                    
                except Exception as e:
                    logger.error(f"Failed to configure range {range_str}: {str(e)}")
                    # Fallback: try individual ports
                    range_ports = self._extract_ports_from_range(range_str)
                    logger.info(f"Exception occurred, falling back to individual port configuration for: {range_ports}")
                    
                    for port in range_ports:
                        try:
                            individual_success = self.change_port_vlan(port, vlan_id, description)
                            if individual_success:
                                # Verify the change
                                verification_status = self.get_port_status(port)
                                if verification_status['current_vlan'] == str(vlan_id):
                                    results['ports_changed'].append(port)
                                else:
                                    results['ports_failed'].append(port)
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
                            # Verify the change
                            verification_status = self.get_port_status(port)
                            if verification_status['current_vlan'] == str(vlan_id):
                                results['ports_changed'].append(port)
                                logger.info(f"Individual port {port} successfully changed and verified to VLAN {vlan_id}")
                            else:
                                results['ports_failed'].append(port)
                                logger.error(f"Individual port {port} configuration appeared successful but verification failed")
                        else:
                            results['ports_failed'].append(port)
                    except Exception as port_e:
                        logger.error(f"Failed to configure individual port {port}: {str(port_e)}")
                        results['ports_failed'].append(port)
            
            # Remove duplicates (in case a port was processed multiple times)
            results['ports_changed'] = list(set(results['ports_changed']))
            results['ports_failed'] = list(set(results['ports_failed']))
            
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

def vlan_change_workflow(switch_id, ports_input, description, vlan_id, vlan_name=None, force_change=False, skip_non_access=False, keep_existing_vlan_name=False, preview_only=False):
    """
    Main VLAN change workflow with comprehensive safety checks.
    
    Args:
        switch_id: Database ID of the target switch
        ports_input: String containing ports (comma-separated, ranges supported)
        description: Description to set on interfaces
        vlan_id: Target VLAN ID
        vlan_name: VLAN name (for creation or update) - optional if keep_existing_vlan_name is True
        force_change: If True, change all ports except uplinks (with confirmation)
        skip_non_access: If True, skip ports that are up or not in access mode
        keep_existing_vlan_name: If True, don't change existing VLAN name
        preview_only: If True, only preview the changes without executing them
    
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
    from app.main import SWITCH_USERNAME, SWITCH_PASSWORD
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
            if not keep_existing_vlan_name and vlan_name and vlan_info['name'] != vlan_name:
                vlan_operation = 'update_name'
            # If keeping existing name, use the current VLAN name from the switch
            elif keep_existing_vlan_name:
                vlan_name = vlan_info['name']
        else:
            if not vlan_name:
                return {'error': 'VLAN name is required when creating a new VLAN', 'status': 'error'}
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
        # Analyze port safety conditions
        logger.info(f"Port analysis: {len(active_or_non_access_ports)} need confirmation, {len(safe_ports)} safe, {len(ports_already_correct)} already correct")
        
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
        
        # If preview_only mode, skip actual changes and just return what would happen
        if preview_only:
            logger.info(f"Preview mode: Simulating changes for VLAN {vlan_id} on ports: {final_ports}")
            # Simulate what would happen
            results['ports_changed'] = final_ports  # Would change these ports
            results['ports_failed'] = []  # Assume success for preview
            
            # Generate what ranges would be used
            if final_ports:
                results['ranges_used'] = vlan_manager.generate_interface_ranges(final_ports)
                
            # Set VLAN operation result for preview
            if vlan_operation == 'create':
                results['vlan_operation_result'] = f'Would create VLAN {vlan_id} with name "{vlan_name}"'
            elif vlan_operation == 'update_name':
                results['vlan_operation_result'] = f'Would update VLAN {vlan_id} name to "{vlan_name}"'
            elif vlan_info['exists']:
                results['vlan_operation_result'] = f'VLAN {vlan_id} already exists with name "{vlan_info["name"]}"'
            
        else:
            # Execute actual changes
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
        
    except Exception as e:
        # Catch any exception that occurs during workflow execution
        logger.error(f"VLAN workflow exception: {str(e)}")
        return {
            'error': f'VLAN workflow failed: {str(e)}',
            'status': 'error',
            'switch_info': switch_info if 'switch_info' in locals() else {'name': f'Switch ID {switch_id}'},
            'vlan_id': vlan_id,
            'exception_details': str(e)
        }
        
    finally:
        if 'vlan_manager' in locals():
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
            required_fields = ['switch_id', 'ports', 'vlan_id']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Optional fields
            description = data.get('description', '')
            vlan_name = data.get('vlan_name')  # Now optional
            keep_existing_vlan_name = data.get('keep_existing_vlan_name', False)
            
            # Safety options - ensure they're mutually exclusive
            force_change = data.get('force_change', False)
            skip_non_access = data.get('skip_non_access', False)
            
            # Convert string 'true'/'false' to boolean if needed
            if isinstance(force_change, str):
                force_change = force_change.lower() == 'true'
            if isinstance(skip_non_access, str):
                skip_non_access = skip_non_access.lower() == 'true'
            if isinstance(data.get('keep_existing_vlan_name'), str):
                keep_existing_vlan_name = data.get('keep_existing_vlan_name', 'false').lower() == 'true'
            
            # Ensure only one safety option is selected at a time
            safety_options_count = sum([force_change, skip_non_access])
            if safety_options_count > 1:
                return jsonify({
                    'error': 'Multiple safety options selected', 
                    'details': 'Please select only one safety option: either "Force change" or "Skip non-access" but not both.'
                }), 400
            
            # Validate VLAN name requirement
            if not keep_existing_vlan_name and not vlan_name:
                return jsonify({
                    'error': 'VLAN name required',
                    'details': 'VLAN name is required unless "Keep existing VLAN name" option is selected.'
                }), 400
            
            # Handle preview_only parameter
            preview_only = data.get('preview_only', False)
            if isinstance(preview_only, str):
                preview_only = preview_only.lower() == 'true'
            
            # Execute workflow
            result = vlan_change_workflow(
                switch_id=data['switch_id'],
                ports_input=data['ports'],
                description=description,
                vlan_id=data['vlan_id'],
                vlan_name=vlan_name,
                force_change=force_change,
                skip_non_access=skip_non_access,
                keep_existing_vlan_name=keep_existing_vlan_name,
                preview_only=preview_only
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
                
                # Use bulk port status for better performance
                if len(ports) > 3:
                    # For multiple ports, use bulk method (much faster)
                    logger.info(f"Using bulk port status for {len(ports)} ports")
                    bulk_statuses = vlan_manager.get_bulk_port_status(ports)
                    port_statuses = []
                    
                    for port in ports:
                        if port in bulk_statuses:
                            status = bulk_statuses[port]
                            status['is_uplink'] = vlan_manager.is_uplink_port(port)
                            port_statuses.append(status)
                        else:
                            # Fallback for missing ports
                            status = vlan_manager.get_port_status(port)
                            status['is_uplink'] = vlan_manager.is_uplink_port(port)
                            port_statuses.append(status)
                else:
                    # For few ports, individual calls are fine
                    logger.info(f"Using individual port status for {len(ports)} ports")
                    port_statuses = []
                    for port in ports:
                        status = vlan_manager.get_port_status(port)
                        status['is_uplink'] = vlan_manager.is_uplink_port(port)
                        port_statuses.append(status)
                
                return jsonify({
                    'ports': port_statuses,
                    'switch_model': switch.model,
                    'optimization_used': 'bulk' if len(ports) > 3 else 'individual'
                })
            finally:
                vlan_manager.disconnect()
                
        except Exception as e:
            logger.error(f"Port status API error: {str(e)}")
            return jsonify({'error': 'Internal server error'}), 500

if __name__ == "__main__":
    # Test the VLAN manager functionality
    pass
