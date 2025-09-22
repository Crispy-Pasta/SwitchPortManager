#!/usr/bin/env python3
"""
Dell Switch Management Module
============================

This module handles SSH connections and operations with Dell switches for the
Dell Switch Port Tracer application.

Features:
- SSH connection management with automatic cleanup
- MAC address table queries
- Port configuration retrieval
- Switch model detection and compatibility
- Uplink port identification
- Connection protection and monitoring integration

Supported Models:
- Dell N2000 Series: N2048 (GigE access, 10GE uplink)
- Dell N3000 Series: N3024P (GigE access, 10GE uplink) 
- Dell N3200 Series: N3248 (10GE access, 25GE uplink)

Author: Network Operations Team
Version: 2.1.3
Last Updated: August 2025
"""

import paramiko
import logging
import time
import re
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from collections import defaultdict
import threading

# Configure logger
logger = logging.getLogger(__name__)

class DellSwitchSSH:
    """Dell switch SSH connection handler with protection monitoring.
    
    This class handles SSH connections to Dell switches with enhanced error handling,
    connection management, and troubleshooting capabilities for network operations.
    
    COMPREHENSIVE TROUBLESHOOTING GUIDE:
    =================================
    CONNECTION ISSUES:
    - Connection Timeouts: Check network connectivity and switch SSH settings
      * Verify switch is reachable: ping <switch_ip>
      * Check TCP port 22 is open: telnet <switch_ip> 22
      * Dell switches default 15-second SSH timeout - check logs for "connection timed out"
    
    - Authentication Failures: Look for "Authentication failed" in logs
      * Verify SWITCH_USERNAME and SWITCH_PASSWORD environment variables are set
      * Check credentials have proper permissions on the switch
      * Ensure switch account is not locked after multiple failed attempts
      * See log message "Failed to connect to <ip>: Authentication failed"
    
    - Session Limits: Dell switches have hard limits on concurrent sessions
      * N2000/N3000/N3200 series limit: maximum 10 concurrent SSH sessions
      * Look for "Connection refused" errors in port_tracer.log
      * Use CPU monitoring to limit concurrent operations per site
      * Verify switch sessions with `show sessions` command
    
    COMMAND EXECUTION ISSUES:
    - Command Timeouts: Output parsing may fail if commands timeout
      * Each command has built-in wait time (1.0 seconds default)
      * Increase wait_time parameter for complex commands
      * Use DEBUG logging to see raw command outputs
      * Check "Executing on <ip>: <command>" log entries
    
    - Lost Connections: Connection drops during long operations
      * Automatic cleanup and reconnection implemented
      * Verify network stability between server and switches
      * Look for "SSH connection to <ip> was closed unexpectedly"
      * Check switch CPU load - high utilization causes drops
    
    MODEL-SPECIFIC BEHAVIORS:
    - Command differences between Dell series:
      * N2000: Older firmware, limited interface range support
      * N3000: Standard CLI with full feature support
      * N3200: Newer syntax, supports 10G access ports
      * Fallback commands implemented for compatibility
    
    LOGGING AND MONITORING:
    - Debug logging: Set LOG_LEVEL=DEBUG for detailed command traces
    - Performance tracking: Monitor command execution times in logs
    - Switch monitoring: Check CPU and memory utilization
    - Log patterns: Look for "SWITCH_MANAGER" prefixed messages
    
    SUPPORTED SWITCH MODELS:
    - Dell N2000 Series: N2048 (GigE access, 10GE uplink)
    - Dell N3000 Series: N3024P (GigE access, 10GE uplink) 
    - Dell N3200 Series: N3248 (10GE access, 25GE uplink)
    """
    
    def __init__(self, ip_address: str, username: str, password: str, switch_monitor=None):
        self.ip_address = ip_address
        self.username = username
        self.password = password
        self.ssh_client = None
        self.shell = None
        self.switch_monitor = switch_monitor
    
    def connect(self) -> bool:
        """Establish SSH connection to the switch with comprehensive Dell compatibility."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info(f"Connecting to {self.ip_address}")
            
            # Try multiple authentication strategies for Dell switch compatibility
            auth_strategies = [
                # Strategy 1: Explicit authentication methods with older algorithm support
                {
                    'hostname': self.ip_address,
                    'username': self.username,
                    'password': self.password,
                    'timeout': 15,
                    'allow_agent': False,
                    'look_for_keys': False,
                    'auth_timeout': 30,
                    'banner_timeout': 30,
                    'disabled_algorithms': {
                        'kex': [],
                        'server_host_key_algorithms': [],
                        'ciphers': [],
                        'macs': []
                    }
                },
                # Strategy 2: Force keyboard-interactive authentication (common on Dell switches)
                {
                    'hostname': self.ip_address,
                    'username': self.username,
                    'password': self.password,
                    'timeout': 15,
                    'allow_agent': False,
                    'look_for_keys': False,
                    'gss_auth': False,
                    'gss_kex': False
                },
                # Strategy 3: Basic connection without restrictions
                {
                    'hostname': self.ip_address,
                    'username': self.username,
                    'password': self.password,
                    'timeout': 15
                }
            ]
            
            last_error = None
            for i, strategy in enumerate(auth_strategies, 1):
                try:
                    self.ssh_client.connect(**strategy)
                    logger.info(f"Successfully connected to {self.ip_address} using strategy {i}")
                    break
                except Exception as e:
                    last_error = e
                    if i < len(auth_strategies):
                        # Close and recreate client for next attempt
                        try:
                            self.ssh_client.close()
                        except:
                            pass
                        self.ssh_client = paramiko.SSHClient()
                        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                # All strategies failed
                raise last_error or Exception("All authentication strategies failed")
            
            # Create interactive shell
            self.shell = self.ssh_client.invoke_shell()
            time.sleep(2)
            
            # Clear initial output
            self.shell.recv(4096)
            
            logger.info(f"Successfully connected to {self.ip_address}")
            return True
            
        except paramiko.AuthenticationException as e:
            logger.error(f"Authentication failed for {self.ip_address}: {str(e)}")
            return False
        except paramiko.SSHException as e:
            logger.error(f"SSH connection error to {self.ip_address}: {str(e)}")
            return False
        except TimeoutError as e:
            logger.error(f"Connection timeout to {self.ip_address}: {str(e)}")
            return False
        except ConnectionRefusedError as e:
            logger.error(f"Connection refused by {self.ip_address}: {str(e)}")
            return False
        except OSError as e:
            logger.error(f"Network error connecting to {self.ip_address}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to {self.ip_address}: {str(e)}")
            return False
    
    def disconnect(self):
        """Close SSH connection."""
        try:
            if self.shell and not self.shell.closed:
                try:
                    self._send_command("exit")
                except:
                    pass
            
            if self.ssh_client:
                self.ssh_client.close()
            
            logger.info(f"Disconnected from {self.ip_address}")
        except Exception as e:
            logger.warning(f"Error during disconnect from {self.ip_address}: {str(e)}")
    
    def _send_command(self, command: str, wait_time: float = 1.0) -> str:
        """Send command to switch and return output."""
        if not self.shell or self.shell.closed:
            raise Exception("No active SSH connection")
        
        try:
            # Command logging for audit purposes only
            self.shell.send(command + '\n')
            time.sleep(wait_time)
            
            output = ""
            while self.shell.recv_ready():
                output += self.shell.recv(4096).decode('utf-8')
            
            return output
            
        except OSError as e:
            if "Socket is closed" in str(e):
                logger.error(f"SSH connection to {self.ip_address} was closed unexpectedly")
                raise Exception("SSH connection lost")
            else:
                raise
    
    def execute_mac_lookup(self, mac_address: str) -> str:
        """Execute MAC address table lookup command."""
        success = False
        try:
            command = f"show mac address-table address {mac_address}"
            logger.info(f"Executing on {self.ip_address}: {command}")
            
            # Use longer wait time for MAC table command
            output = self._send_command(command, wait_time=3.0)
            
            # Try to get any remaining output
            time.sleep(2)
            if self.shell.recv_ready():
                additional_output = ""
                while self.shell.recv_ready():
                    additional_output += self.shell.recv(4096).decode('utf-8')
                output += additional_output
            
            logger.info(f"Command completed on {self.ip_address}, output: {len(output)} chars")
            success = True
            return output
            
        except Exception as e:
            logger.error(f"Failed to execute MAC lookup on {self.ip_address}: {str(e)}")
            raise
        finally:
            # Record command execution for monitoring
            if self.switch_monitor:
                self.switch_monitor.record_command_execution(self.ip_address, success)
    
    def get_port_config(self, port_name: str) -> Dict[str, Any]:
        """Get port configuration including mode and description."""
        try:
            command = f"show running-config interface {port_name}"
            logger.info(f"Getting port config for {port_name} on {self.ip_address}")
            
            output = self._send_command(command, wait_time=2.0)
            
            # Try to get any remaining output
            time.sleep(1.5)
            if self.shell.recv_ready():
                additional_output = ""
                while self.shell.recv_ready():
                    additional_output += self.shell.recv(4096).decode('utf-8')
                output += additional_output
            
            return self._parse_port_config(output)
            
        except Exception as e:
            logger.error(f"Failed to get port config for {port_name} on {self.ip_address}: {str(e)}")
            return {'mode': 'unknown', 'description': '', 'vlans': []}
    
    def _parse_port_config(self, output: str) -> Dict[str, Any]:
        """Parse port configuration output."""
        config = {
            'mode': 'unknown',
            'description': '',
            'vlans': [],
            'pvid': ''
        }
        
        if not output:
            return config
        
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract description
            if line.startswith('description'):
                # Remove 'description' and quotes
                desc = line[11:].strip()
                if desc.startswith('"') and desc.endswith('"'):
                    desc = desc[1:-1]
                config['description'] = desc
            
            # Extract switchport mode
            elif 'switchport mode' in line:
                if 'access' in line:
                    config['mode'] = 'access'
                elif 'trunk' in line:
                    config['mode'] = 'trunk'
                elif 'general' in line:
                    config['mode'] = 'general'
            
            # Extract PVID for general mode
            elif 'switchport general pvid' in line:
                parts = line.split()
                if len(parts) >= 4:
                    config['pvid'] = parts[3]
            
            # Extract allowed VLANs
            elif 'switchport general allowed vlan add' in line or 'switchport trunk allowed vlan add' in line:
                # Extract VLAN numbers
                vlan_part = line.split('add')[-1].strip()
                if 'tagged' in vlan_part:
                    vlan_part = vlan_part.replace('tagged', '').strip()
                config['vlans'].append(vlan_part)
            
            # Access VLAN
            elif 'switchport access vlan' in line:
                parts = line.split()
                if len(parts) >= 4:
                    config['vlans'] = [parts[3]]
        
        return config


def detect_switch_model_from_config(switch_name: str, switch_config: Dict[str, Any]) -> str:
    """Detect switch model from configuration or name patterns."""
    model = switch_config.get('model', '').upper()
    
    # Extract model from explicit model field with specific N3248 variant detection
    # Check for N3248PXE first (Te ports are uplinks)
    if 'N3248PXE' in model or 'N3248-PXE' in model:
        return 'N3248PXE'
    # Check for N3248P (Gi ports are uplinks) 
    elif 'N3248P' in model:
        return 'N3248P'
    # Check for base N3248 (assume Te ports are uplinks like N3200)
    elif 'N3248' in model:
        return 'N3200'
    elif 'N2000' in model or 'N20' in model:
        return 'N2000'
    elif 'N3200' in model or 'N32' in model:
        return 'N3200' 
    elif 'N3000' in model or 'N30' in model:
        return 'N3000'
    
    # Fallback: try to infer from switch name patterns
    name_upper = switch_name.upper()
    if any(pattern in name_upper for pattern in ['N2000', 'N20']):
        return 'N2000'
    elif any(pattern in name_upper for pattern in ['N3248PXE', 'N3248-PXE']):
        return 'N3248PXE'
    elif any(pattern in name_upper for pattern in ['N3248P']):
        return 'N3248P'
    elif any(pattern in name_upper for pattern in ['N3200', 'N32', 'N3248']):
        return 'N3200'
    elif any(pattern in name_upper for pattern in ['N3000', 'N30']):
        return 'N3000'
    
    # Default assumption (only if unknown model)
    return 'N3000'


def is_uplink_port(port_name: str, switch_model: Optional[str] = None, port_description: str = '') -> bool:
    """Determine if a port is an uplink based on Dell switch series and port characteristics."""
    
    # Always filter out Port-Channels
    if port_name.startswith('Po'):
        return True
        
    # Check description for uplink indicators - prioritize description-based detection
    if port_description:
        uplink_keywords = ['UPLINK', 'uplink', 'Uplink', 'CS', 'cs', 'Cs', 'TRUNK', 'trunk', 'Trunk', 'CORE', 'core', 'Core']
        if any(keyword in port_description for keyword in uplink_keywords):
            return True
    
    # Model-specific uplink port detection (only if no description indicators)
    if switch_model == 'N2000':
        # N2000: Gi ports are access, Te ports are uplinks
        return port_name.startswith('Te')
    elif switch_model == 'N3000': 
        # N3000: Gi ports are access, Te ports are uplinks
        return port_name.startswith('Te')
    elif switch_model == 'N3248P':
        # N3248P: Gi ports are access, Te ports are uplinks (like standard N3000)
        return port_name.startswith('Te')
    elif switch_model == 'N3248PXE':
        # N3248PXE: Te ports are access, Tw ports are uplinks (like N3200)
        return port_name.startswith('Tw')
    elif switch_model == 'N3200':
        # N3200: Te ports are access, Tw (TwentyGig) ports are uplinks
        return port_name.startswith('Tw')
    
    # Generic fallback - common uplink port patterns
    uplink_patterns = ['Te', 'Tw', 'Fo']  # TenGig, TwentyGig, FortyGig
    return any(port_name.startswith(pattern) for pattern in uplink_patterns)


def is_wlan_ap_port(port_description: str = '', port_vlans: Optional[List] = None) -> bool:
    """Determine if a port is likely connected to WLAN/AP based on description and VLAN configuration."""
    
    # Check description for WLAN/AP indicators
    if port_description:
        wlan_keywords = ['WLAN', 'wlan', 'Wlan', 'AP', 'ap', 'Wi-Fi', 'wifi', 'WiFi', 'WIRELESS', 'wireless', 'Wireless', 'ACCESS POINT', 'access point']
        if any(keyword in port_description for keyword in wlan_keywords):
            return True
    
    # Check for multiple VLANs (typical for AP trunk ports)
    if port_vlans and isinstance(port_vlans, list):
        # If port has many VLANs (more than 3), it's likely an AP or trunk port
        total_vlans = 0
        for vlan_range in port_vlans:
            if '-' in str(vlan_range):  # VLAN range like "10-20"
                try:
                    start, end = map(int, str(vlan_range).split('-'))
                    total_vlans += (end - start + 1)
                except:
                    total_vlans += 1
            elif ',' in str(vlan_range):  # Multiple VLANs like "10,20,30"
                total_vlans += len(str(vlan_range).split(','))
            else:
                total_vlans += 1
        
        if total_vlans > 3:  # More than 3 VLANs suggests AP or trunk
            return True
    
    return False


def get_port_caution_info(port_name: str, switch_model: Optional[str] = None, 
                         port_description: str = '', port_mode: str = '', 
                         port_vlans: Optional[List] = None) -> List[Dict[str, Any]]:
    """Get caution information for a port based on its characteristics.
    
    Priority order:
    1. AP/WLAN detection (from description) - HIGHEST PRIORITY
    2. Uplink detection (from description) - HIGH PRIORITY  
    3. Generic port-based uplink detection - LOWEST PRIORITY
    """
    cautions = []
    
    # PRIORITY 1: Check for AP/WLAN ports FIRST (highest priority)
    # AP connections should never be flagged as uplinks even if they're on Te ports
    ap_detected = False
    if port_description:
        wlan_keywords = ['WLAN', 'wlan', 'Wlan', 'AP', 'ap', 'Wi-Fi', 'wifi', 'WiFi', 
                        'WIRELESS', 'wireless', 'Wireless', 'ACCESS POINT', 'access point']
        if any(keyword in port_description for keyword in wlan_keywords):
            cautions.append({
                'type': 'wlan_ap',
                'icon': '⚠️',
                'message': 'Possible AP Connection'
            })
            ap_detected = True
    
    # PRIORITY 2: Check for uplink ports ONLY if NOT an AP
    if not ap_detected:
        uplink_detected = False
        
        # Check description for explicit uplink indicators
        if port_description:
            uplink_keywords = ['UPLINK', 'uplink', 'Uplink', 'CS', 'cs', 'Cs', 'TRUNK', 'trunk', 'Trunk', 'CORE', 'core', 'Core']
            if any(keyword in port_description for keyword in uplink_keywords):
                uplink_detected = True
        
        # PRIORITY 3: Only use generic port name patterns if no description clues
        if not uplink_detected and not port_description:
            # Only check port patterns if there's NO description to guide us
            if is_uplink_port(port_name, switch_model, ''):
                uplink_detected = True
        
        if uplink_detected:
            cautions.append({
                'type': 'uplink',
                'icon': '🚨',
                'message': 'Possible Switch Uplink'
            })
    
    # Check for trunk/general ports with many VLANs (additional caution)
    if port_mode in ['trunk', 'general'] and port_vlans:
        total_vlans = 0
        for vlan_range in port_vlans:
            if '-' in str(vlan_range):
                try:
                    start, end = map(int, str(vlan_range).split('-'))
                    total_vlans += (end - start + 1)
                except:
                    total_vlans += 1
            elif ',' in str(vlan_range):
                total_vlans += len(str(vlan_range).split(','))
            else:
                total_vlans += 1
        
        # Removed trunk_many_vlans caution as requested
        pass
    
    return cautions


def parse_mac_table_output(output: str, target_mac: str) -> Dict[str, Any]:
    """Parse the MAC address table output from Dell switch."""
    if not output or len(output.strip()) == 0:
        return {'found': False, 'message': 'Empty output received'}
    
    lines = output.split('\n')
    
    # Convert target MAC to dotted format (C0:EA:E4:85:7F:CA -> C0EA.E485.7FCA)
    # Normalize MAC address to format without delimiters for easy comparison
    target_mac_clean = target_mac.replace(':', '').replace('-', '').replace('.', '').upper()
    target_mac_dotted = f"{target_mac_clean[:4]}.{target_mac_clean[4:8]}.{target_mac_clean[8:]}"
    
    # Parse each line looking for the MAC
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('-') or 'Address' in line or 'Total' in line:
            continue
            
        # Split by whitespace
        parts = line.split()
        if len(parts) >= 4:
            mac_in_line = parts[1] if len(parts) > 1 else ""
            
            if mac_in_line.upper() == target_mac_dotted:
                vlan = parts[0]
                mac_type = parts[2]
                port = parts[3] if len(parts) > 3 else "Unknown"
                
                # Filter out uplink ports (Port-Channels and common uplink ports)
                if port.startswith('Po') or 'Uplink' in port or port in ['Gi1/0/47', 'Gi1/0/48', 'Te1/0/1', 'Te1/0/2']:
                    return {'found': False, 'message': f'MAC found on uplink port {port} - excluding from results'}
                
                return {
                    'found': True,
                    'vlan': vlan,
                    'mac': mac_in_line,
                    'port': port,
                    'type': mac_type,
                    'line': line
                }
    
    return {'found': False, 'message': 'MAC address not found'}


def trace_single_switch(switch_info: Dict[str, Any], mac_address: str, username: str, 
                       switch_monitor=None) -> Dict[str, Any]:
    """Trace MAC address on a single switch - designed for concurrent execution."""
    switch_ip = switch_info['ip']
    switch_name = switch_info['name']
    
    # Check switch-side protection limits before attempting connection
    if switch_monitor:
        try:
            if not switch_monitor.acquire_switch_connection(switch_ip, username):
                return {
                    'switch_name': switch_name,
                    'switch_ip': switch_ip,
                    'status': 'connection_rejected',
                    'message': 'Switch connection rejected due to protection limits. Please try again in a moment.'
                }
        except AttributeError:
            # If switch_monitor doesn't have the method, continue without protection
            pass
    
    try:
        # Attempting connection to switch
        
        # Import credentials from environment variables
        import os
        username = os.getenv('SWITCH_USERNAME')
        password = os.getenv('SWITCH_PASSWORD')
        
        switch = DellSwitchSSH(switch_ip, username, password, switch_monitor)
        
        if not switch.connect():
            # Determine specific connection failure reason
            return {
                'switch_name': switch_name,
                'switch_ip': switch_ip,
                'status': 'connection_failed',
                'message': get_connection_failure_message(switch_ip)
            }
        
        # Execute MAC lookup
        output = switch.execute_mac_lookup(mac_address)
        result = parse_mac_table_output(output, mac_address)
        
        if result['found']:
            # Get detailed port configuration
            port_config = switch.get_port_config(result['port'])
            
            # Detect switch model for accurate caution detection
            switch_model = detect_switch_model_from_config(switch_name, {'model': 'N3000'})
            
            # Get caution information for this port
            cautions = get_port_caution_info(
                port_name=result['port'],
                switch_model=switch_model,
                port_description=port_config.get('description', ''),
                port_mode=port_config.get('mode', ''),
                port_vlans=port_config.get('vlans', [])
            )
            
            return {
                'switch_name': switch_name,
                'switch_ip': switch_ip,
                'status': 'found',
                'vlan': result['vlan'],
                'port': result['port'],
                'type': result['type'],
                'mac': result['mac'],
                'port_mode': port_config.get('mode', 'unknown'),
                'port_description': port_config.get('description', ''),
                'port_pvid': port_config.get('pvid', ''),
                'port_vlans': port_config.get('vlans', []),
                'cautions': cautions  # Add caution information
            }
        else:
            return {
                'switch_name': switch_name,
                'switch_ip': switch_ip,
                'status': 'not_found',
                'message': result['message']
            }
        
    except paramiko.AuthenticationException as e:
        logger.error(f"Authentication failed for {switch_name} ({switch_ip}): {str(e)}")
        return {
            'switch_name': switch_name,
            'switch_ip': switch_ip,
            'status': 'authentication_failed',
            'message': 'Authentication failed - please check switch credentials'
        }
    except paramiko.SSHException as e:
        logger.error(f"SSH error for {switch_name} ({switch_ip}): {str(e)}")
        return {
            'switch_name': switch_name,
            'switch_ip': switch_ip,
            'status': 'ssh_error',
            'message': f'SSH connection error: {get_ssh_error_message(str(e))}'
        }
    except (TimeoutError, ConnectionRefusedError, OSError) as e:
        logger.error(f"Network error for {switch_name} ({switch_ip}): {str(e)}")
        return {
            'switch_name': switch_name,
            'switch_ip': switch_ip,
            'status': 'network_unreachable',
            'message': f'Device unreachable - {get_network_error_message(str(e))}'
        }
    except Exception as e:
        logger.error(f"Unexpected error tracing MAC on {switch_name} ({switch_ip}): {str(e)}")
        return {
            'switch_name': switch_name,
            'switch_ip': switch_ip,
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }
    finally:
        # Ensure connection is always closed
        try:
            if 'switch' in locals():
                switch.disconnect()
        except:
            pass
        
        # Always release switch connection slot
        if switch_monitor:
            try:
                switch_monitor.release_switch_connection(switch_ip, username)
            except AttributeError:
                # If switch_monitor doesn't have the method, continue
                pass


# Error message helper functions for better user experience
def get_connection_failure_message(switch_ip: str) -> str:
    """Generate user-friendly message for connection failures."""
    return f"Unable to connect to switch {switch_ip}. The device may be offline, unreachable, or have connectivity issues. Please check network connectivity and try again."


def get_network_error_message(error_str: str) -> str:
    """Convert technical network errors into user-friendly messages."""
    error_lower = error_str.lower()
    
    if 'timeout' in error_lower or 'timed out' in error_lower:
        return "Connection timed out. The device may be busy or network latency is high."
    elif 'refused' in error_lower or 'connection refused' in error_lower:
        return "Connection refused. The device may be down or SSH service is disabled."
    elif 'unreachable' in error_lower or 'no route' in error_lower:
        return "Network unreachable. Check network connectivity and routing."
    elif 'name resolution' in error_lower or 'resolve' in error_lower:
        return "Name resolution failed. Please verify the IP address is correct."
    else:
        return "Check network connectivity and device availability."


def get_ssh_error_message(error_str: str) -> str:
    """Convert SSH-specific errors into user-friendly messages."""
    error_lower = error_str.lower()
    
    if 'authentication' in error_lower:
        return "Invalid credentials or authentication method not supported"
    elif 'key exchange' in error_lower or 'kex' in error_lower:
        return "SSH key exchange failed. The device may use incompatible encryption"
    elif 'protocol' in error_lower:
        return "SSH protocol mismatch. The device may use an unsupported SSH version"
    elif 'banner' in error_lower:
        return "SSH banner timeout. The device may be slow to respond"
    elif 'channel' in error_lower:
        return "SSH channel error. The connection was interrupted"
    else:
        return "SSH connection issue. Check device SSH configuration"
