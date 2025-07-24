#!/usr/bin/env python3
"""
Comprehensive Dell Switch Model Discovery Script

Connects to ALL Dell switches via SSH across all sites and floors, runs 'show version' 
to determine the actual switch model, and provides detailed mismatch reporting.

Supported Dell Switch Series:
- N2000 Series (e.g., N2048) - GigE access ports, 10GE uplinks
- N3000 Series (e.g., N3024P) - GigE access ports, 10GE uplinks  
- N3200 Series (e.g., N3248) - 10GE access ports, 25GE uplinks

This script enables accurate port categorization for role-based filtering in the
port tracer web application by ensuring switch models are correctly identified.
"""

import paramiko
import json
import time
import logging
import os
from typing import Dict, Any, Optional
import copy
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SSH credentials from environment variables
SSH_USERNAME = os.getenv('SSH_USERNAME', 'estradajan')
SSH_PASSWORD = os.getenv('SSH_PASSWORD', 'Jironjio010812!!')
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

def discover_all_switches(switches_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Check all switches in all sites and return model updates."""
    all_results = {}
    total_switches = 0
    processed_switches = 0
    
    # Count total switches first
    sites = switches_data.get('sites', {})
    for site_name, site_data in sites.items():
        for floor_name, floor_data in site_data.get('floors', {}).items():
            for switch_name, switch_config in floor_data.get('switches', {}).items():
                if switch_config.get('enabled', True):
                    total_switches += 1
    
    logger.info(f"Starting comprehensive discovery for {total_switches} switches across {len(sites)} sites")
    
    for site_name, site_data in sites.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing Site: {site_name}")
        logger.info(f"{'='*60}")
        
        site_results = {}
        
        for floor_name, floor_data in site_data.get('floors', {}).items():
            logger.info(f"\n--- Floor {floor_name} ---")
            
            floor_switches = floor_data.get('switches', {})
            if not floor_switches:
                logger.info(f"No switches found on floor {floor_name}")
                continue
                
            for switch_name, switch_config in floor_switches.items():
                if not switch_config.get('enabled', True):
                    logger.info(f"Skipping disabled switch: {switch_name}")
                    continue
                
                processed_switches += 1
                ip_address = switch_config['ip_address']
                current_model = switch_config.get('model', 'Unknown')
                
                logger.info(f"[{processed_switches}/{total_switches}] Checking {switch_name} ({ip_address}) - Current: {current_model}")
                
                # Connect to switch
                ssh_client = connect_to_switch(ip_address, SSH_USERNAME, SSH_PASSWORD)
                if not ssh_client:
                    site_results[switch_name] = {
                        'status': 'CONNECTION_FAILED',
                        'current_model': current_model,
                        'actual_model': 'Unknown',
                        'ip': ip_address
                    }
                    continue
                
                # Get version info
                version_output = get_switch_version(ssh_client)
                ssh_client.close()
                
                if not version_output:
                    site_results[switch_name] = {
                        'status': 'VERSION_FAILED',
                        'current_model': current_model,
                        'actual_model': 'Unknown',
                        'ip': ip_address
                    }
                    continue
                
                # Parse model
                actual_model = parse_switch_model(version_output)
                
                if actual_model != current_model:
                    logger.warning(f"✗ Model mismatch: {switch_name} - Expected: {current_model}, Actual: {actual_model}")
                    site_results[switch_name] = {
                        'status': 'MISMATCH',
                        'current_model': current_model,
                        'actual_model': actual_model,
                        'ip': ip_address
                    }
                else:
                    logger.info(f"✓ Model confirmed: {switch_name} - {actual_model}")
                    site_results[switch_name] = {
                        'status': 'CONFIRMED',
                        'current_model': current_model,
                        'actual_model': actual_model,
                        'ip': ip_address
                    }
                
                # Small delay between switches to be nice to the network
                time.sleep(1)
        
        all_results[site_name] = site_results
    
    return all_results

def update_switches_json(switches_data: Dict[str, Any], discovery_results: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """Update the switches data with discovered models."""
    updated_data = copy.deepcopy(switches_data)
    updates_made = 0
    
    for site_name, site_results in discovery_results.items():
        if site_name not in updated_data.get('sites', {}):
            continue
            
        site_data = updated_data['sites'][site_name]
        
        for floor_name, floor_data in site_data.get('floors', {}).items():
            for switch_name, switch_config in floor_data.get('switches', {}).items():
                if switch_name in site_results:
                    result = site_results[switch_name]
                    if result['status'] == 'MISMATCH' and result['actual_model'] != 'Unknown':
                        # Update the model
                        old_model = switch_config.get('model', 'Unknown')
                        switch_config['model'] = result['actual_model']
                        logger.info(f"Updated {switch_name}: {old_model} -> {result['actual_model']}")
                        updates_made += 1
    
    logger.info(f"Total model updates made: {updates_made}")
    return updated_data

def generate_discovery_report(discovery_results: Dict[str, Dict[str, str]]) -> str:
    """Generate a detailed discovery report."""
    report = []
    report.append(f"DELL SWITCH MODEL DISCOVERY REPORT")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"=" * 80)
    
    total_switches = 0
    confirmed = 0
    mismatched = 0
    failed = 0
    
    for site_name, site_results in discovery_results.items():
        report.append(f"\nSITE: {site_name}")
        report.append(f"-" * 60)
        
        for switch_name, result in site_results.items():
            total_switches += 1
            status = result['status']
            current = result['current_model']
            actual = result['actual_model']
            ip = result['ip']
            
            if status == 'CONFIRMED':
                confirmed += 1
                status_icon = "✓"
            elif status == 'MISMATCH':
                mismatched += 1
                status_icon = "✗"
            else:
                failed += 1
                status_icon = "⚠"
            
            report.append(f"{status_icon} {switch_name:<25} | {ip:<15} | {current:<12} -> {actual:<12} | {status}")
    
    report.append(f"\n" + "=" * 80)
    report.append(f"SUMMARY:")
    report.append(f"Total switches checked: {total_switches}")
    report.append(f"Models confirmed:       {confirmed}")
    report.append(f"Models mismatched:      {mismatched}")
    report.append(f"Connection/Check failed: {failed}")
    report.append(f"=" * 80)
    
    return "\n".join(report)

def main():
    """Main function to discover all switch models."""
    logger.info("Starting comprehensive Dell switch model discovery...")
    
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
    
    # Discover all switches
    discovery_results = discover_all_switches(switches_data)
    
    # Generate and display report
    report = generate_discovery_report(discovery_results)
    print(f"\n{report}")
    
    # Save report to file
    with open(f'switch_discovery_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt', 'w') as f:
        f.write(report)
    
    # Check if any updates are needed
    mismatches = []
    for site_name, site_results in discovery_results.items():
        for switch_name, result in site_results.items():
            if result['status'] == 'MISMATCH':
                mismatches.append(f"{site_name} - {switch_name}: {result['current_model']} -> {result['actual_model']}")
    
    if mismatches:
        print(f"\nFound {len(mismatches)} switches with model mismatches!")
        print("Mismatches found:")
        for mismatch in mismatches[:10]:  # Show first 10
            print(f"  • {mismatch}")
        if len(mismatches) > 10:
            print(f"  ... and {len(mismatches) - 10} more")
        
        response = input(f"\nDo you want to update switches.json with the correct models? (y/n): ")
        if response.lower() == 'y':
            # Update switches.json
            updated_data = update_switches_json(switches_data, discovery_results)
            
            # Create backup
            backup_file = f'switches_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(backup_file, 'w') as f:
                json.dump(switches_data, f, indent=2)
            logger.info(f"Original switches.json backed up to: {backup_file}")
            
            # Save updated file
            with open('switches.json', 'w') as f:
                json.dump(updated_data, f, indent=2)
            logger.info("switches.json updated with correct models!")
            
            print(f"\n✅ Updated switches.json successfully!")
            print(f"   • Backup saved as: {backup_file}")
            print(f"   • Discovery report saved as: switch_discovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        else:
            print("No changes made to switches.json")
    else:
        print(f"\n✅ All switch models are correctly configured!")

if __name__ == "__main__":
    main()
