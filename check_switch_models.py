#!/usr/bin/env python3
"""
Switch Model Discovery Script

Connects to Dell switches via SSH and runs 'show version' to determine 
the actual switch model, then updates the switches.json file accordingly.
"""

import paramiko
import json
import time
import logging
import os
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SSH credentials from environment variables
SSH_USERNAME = os.getenv('SSH_USERNAME', 'admin')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', 'your_password')
SSH_TIMEOUT = 15

def connect_to_switch(ip_address: str, username: str, password: str) -> Optional[paramiko.SSHClient]:
    """Connect to a Dell switch via SSH."""
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        logger.info(f"Connecting to {ip_address}...")
        ssh_client.connect(
            hostname=ip_address,
            username=username,
            password=password,
            timeout=SSH_TIMEOUT
        )
        return ssh_client
    except Exception as e:
        logger.error(f"Failed to connect to {ip_address}: {str(e)}")
        return None

def get_switch_version(ssh_client: paramiko.SSHClient) -> Optional[str]:
    """Execute 'show version' command and extract model information."""
    try:
        # Create interactive shell
        shell = ssh_client.invoke_shell()
        time.sleep(2)
        
        # Clear initial output
        shell.recv(4096)
        
        # Send show version command
        shell.send('show version\n')
        time.sleep(3)
        
        # Collect output
        output = ""
        while shell.recv_ready():
            output += shell.recv(4096).decode('utf-8')
        
        # Send exit
        shell.send('exit\n')
        shell.close()
        
        return output
    except Exception as e:
        logger.error(f"Failed to execute show version: {str(e)}")
        return None

def parse_switch_model(version_output: str) -> str:
    """Parse the show version output to extract the actual switch model."""
    if not version_output:
        return "Unknown"
    
    lines = version_output.split('\n')
    
    for line in lines:
        line = line.strip().upper()
        
        # Look for common Dell switch model patterns
        if 'N3248' in line or 'POWERCONNECT N3248' in line:
            return 'Dell N3248'
        elif 'N3224' in line or 'POWERCONNECT N3224' in line:
            return 'Dell N3224'
        elif 'N3132' in line or 'POWERCONNECT N3132' in line:
            return 'Dell N3132'
        elif 'N3048' in line or 'POWERCONNECT N3048' in line:
            return 'Dell N3048'
        elif 'N3024' in line or 'POWERCONNECT N3024' in line:
            return 'Dell N3024'
        elif 'N2048' in line or 'POWERCONNECT N2048' in line:
            return 'Dell N2048'
        elif 'N2024' in line or 'POWERCONNECT N2024' in line:
            return 'Dell N2024'
        elif 'N3200' in line:
            return 'Dell N3200'
        elif 'N3000' in line:
            return 'Dell N3000'
        elif 'N2000' in line:
            return 'Dell N2000'
        elif 'POWERCONNECT' in line and ('N30' in line or 'N20' in line):
            # Generic fallback for PowerConnect series
            if 'N30' in line:
                return 'Dell N3000'
            elif 'N20' in line:
                return 'Dell N2000'
    
    # If no specific model found, look for Dell/PowerConnect indicators
    for line in lines:
        line = line.strip().upper()
        if 'DELL' in line or 'POWERCONNECT' in line:
            logger.warning(f"Found Dell switch but couldn't determine exact model from: {line}")
            return 'Dell N3000'  # Default assumption
    
    return "Unknown"

def check_switches_in_site(switches_data: Dict[str, Any], site_name: str) -> Dict[str, str]:
    """Check all switches in a specific site and return model updates."""
    results = {}
    
    if site_name not in switches_data.get('sites', {}):
        logger.error(f"Site '{site_name}' not found in switches data")
        return results
    
    site_data = switches_data['sites'][site_name]
    
    for floor_name, floor_data in site_data.get('floors', {}).items():
        logger.info(f"Checking {site_name} - Floor {floor_name}")
        
        for switch_name, switch_config in floor_data.get('switches', {}).items():
            if not switch_config.get('enabled', True):
                logger.info(f"Skipping disabled switch: {switch_name}")
                continue
            
            ip_address = switch_config['ip_address']
            current_model = switch_config.get('model', 'Unknown')
            
            logger.info(f"Checking {switch_name} ({ip_address}) - Current model: {current_model}")
            
            # Connect to switch
            ssh_client = connect_to_switch(ip_address, SSH_USERNAME, SSH_PASSWORD)
            if not ssh_client:
                results[switch_name] = f"CONNECTION_FAILED (was: {current_model})"
                continue
            
            # Get version info
            version_output = get_switch_version(ssh_client)
            ssh_client.close()
            
            if not version_output:
                results[switch_name] = f"VERSION_FAILED (was: {current_model})"
                continue
            
            # Parse model
            actual_model = parse_switch_model(version_output)
            
            if actual_model != current_model:
                logger.warning(f"Model mismatch for {switch_name}: Current={current_model}, Actual={actual_model}")
                results[switch_name] = f"UPDATED: {current_model} -> {actual_model}"
            else:
                logger.info(f"Model confirmed for {switch_name}: {actual_model}")
                results[switch_name] = f"CONFIRMED: {actual_model}"
    
    return results

def main():
    """Main function to check switch models."""
    # Load switches configuration
    try:
        with open('switches.json', 'r') as f:
            switches_data = json.load(f)
    except FileNotFoundError:
        logger.error("switches.json not found")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in switches.json: {e}")
        return
    
    # Check SM Aura site
    site_name = "SM Aura"
    logger.info(f"Starting model discovery for site: {site_name}")
    
    results = check_switches_in_site(switches_data, site_name)
    
    # Display results
    print(f"\n{'='*60}")
    print(f"SWITCH MODEL DISCOVERY RESULTS - {site_name}")
    print(f"{'='*60}")
    
    for switch_name, result in results.items():
        print(f"{switch_name:25} | {result}")
    
    print(f"{'='*60}")
    print(f"Total switches checked: {len(results)}")
    
    # Ask if user wants to update the switches.json file
    update_needed = any("UPDATED:" in result for result in results.values())
    if update_needed:
        print(f"\nFound switches with model mismatches!")
        response = input("Do you want to update switches.json with the correct models? (y/n): ")
        if response.lower() == 'y':
            # Update switches.json (implementation would go here)
            print("Note: Automatic update not implemented yet. Please update manually based on results above.")

if __name__ == "__main__":
    main()
