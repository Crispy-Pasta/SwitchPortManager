#!/usr/bin/env python3
"""
Script to update specific switch models and add port categorization for N2000 series switches.
This script updates the switches.json file with correct models and adds port categorization.
"""

import json
import logging
from datetime import datetime
import os
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('switch_model_updates.log'),
        logging.StreamHandler()
    ]
)

def create_backup(file_path):
    """Create a backup of the original file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    logging.info(f"Backup created: {backup_path}")
    return backup_path

def add_port_categorization(switches_data):
    """Add port categorization structure to switches data"""
    
    # Define N2000 series port categorization (gi for ports, Te for uplinks)
    n2000_series_port_config = {
        "Dell N2224PX": {
            "series": "N2000",
            "port_types": {
                "access_ports": {
                    "prefix": "gi",
                    "range": "1/0/1-1/0/24",
                    "description": "Gigabit Ethernet access ports"
                },
                "uplink_ports": {
                    "prefix": "Te", 
                    "range": "1/0/25-1/0/28",
                    "description": "10 Gigabit Ethernet uplink ports"
                }
            }
        },
        "Dell N1548P": {
            "series": "N2000",
            "port_types": {
                "access_ports": {
                    "prefix": "gi",
                    "range": "1/0/1-1/0/48",
                    "description": "Gigabit Ethernet access ports"
                },
                "uplink_ports": {
                    "prefix": "Te",
                    "range": "1/0/49-1/0/52", 
                    "description": "10 Gigabit Ethernet uplink ports"
                }
            }
        },
        "Dell N1548": {
            "series": "N2000",
            "port_types": {
                "access_ports": {
                    "prefix": "gi",
                    "range": "1/0/1-1/0/48",
                    "description": "Gigabit Ethernet access ports"
                },
                "uplink_ports": {
                    "prefix": "Te",
                    "range": "1/0/49-1/0/52",
                    "description": "10 Gigabit Ethernet uplink ports"
                }
            }
        }
    }
    
    # Add port categorization to the switches data structure
    if "port_categorization" not in switches_data:
        switches_data["port_categorization"] = {}
    
    switches_data["port_categorization"]["N2000_series"] = n2000_series_port_config
    
    logging.info("Added N2000 series port categorization")
    return switches_data

def update_specific_switches(switches_data):
    """Update specific switches with correct models"""
    
    # Define the switches to update
    updates = [
        {
            "ip": "192.168.0.246",
            "new_model": "Dell N2224PX",
            "description": "Updated to correct model N2224PX"
        },
        {
            "ip": "192.168.0.247", 
            "new_model": "Dell N1548P",
            "description": "Updated to correct model N1548P"
        },
        {
            "ip": "10.60.0.7",
            "new_model": "Dell N1548P", 
            "description": "Updated to correct model N1548P"
        },
        {
            "ip": "10.60.0.10",
            "new_model": "Dell N1548",
            "description": "Updated to correct model N1548"
        }
    ]
    
    updates_made = []
    
    # Search and update switches
    for site_name, site_data in switches_data["sites"].items():
        for floor_num, floor_data in site_data["floors"].items():
            for switch_name, switch_data in floor_data["switches"].items():
                current_ip = switch_data["ip_address"]
                
                # Check if this switch needs updating
                for update in updates:
                    if current_ip == update["ip"]:
                        old_model = switch_data["model"]
                        switch_data["model"] = update["new_model"]
                        
                        # Add series classification for N2000 series switches
                        if update["new_model"] in ["Dell N2224PX", "Dell N1548P", "Dell N1548"]:
                            switch_data["series"] = "N2000"
                            switch_data["port_category"] = "gi_te_ports"
                        
                        updates_made.append({
                            "switch_name": switch_name,
                            "site": site_name,
                            "floor": floor_num,
                            "ip": current_ip,
                            "old_model": old_model,
                            "new_model": update["new_model"],
                            "description": update["description"]
                        })
                        
                        logging.info(f"Updated {switch_name} ({current_ip}): {old_model} → {update['new_model']}")
                        break
    
    return switches_data, updates_made

def generate_update_report(updates_made, backup_path):
    """Generate a detailed update report"""
    
    report_lines = [
        "SWITCH MODEL UPDATE REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 80,
        "",
        f"Backup created: {backup_path}",
        "",
        "UPDATES APPLIED:",
        "-" * 40
    ]
    
    if not updates_made:
        report_lines.append("No updates were applied.")
    else:
        for update in updates_made:
            report_lines.extend([
                f"Switch: {update['switch_name']}",
                f"Site: {update['site']} (Floor {update['floor']})", 
                f"IP Address: {update['ip']}",
                f"Model Change: {update['old_model']} → {update['new_model']}",
                f"Description: {update['description']}",
                f"Series: N2000 (gi for ports, Te for uplinks)",
                ""
            ])
    
    report_lines.extend([
        "=" * 80,
        "SUMMARY:",
        f"Total switches updated: {len(updates_made)}",
        "",
        "PORT CATEGORIZATION ADDED:",
        "- N2000 series switches now have port categorization",
        "- gi prefix for access ports (Gigabit Ethernet)",
        "- Te prefix for uplink ports (10 Gigabit Ethernet)",
        "",
        "Models updated:",
        "- Dell N2224PX: 24 gi ports + 4 Te uplinks",
        "- Dell N1548P: 48 gi ports + 4 Te uplinks", 
        "- Dell N1548: 48 gi ports + 4 Te uplinks",
        "=" * 80
    ])
    
    return "\n".join(report_lines)

def main():
    """Main function to perform the updates"""
    
    switches_file = "switches.json"
    
    if not os.path.exists(switches_file):
        logging.error(f"File {switches_file} not found!")
        return
    
    try:
        # Load the switches data
        logging.info(f"Loading {switches_file}...")
        with open(switches_file, 'r', encoding='utf-8') as f:
            switches_data = json.load(f)
        
        # Create backup
        backup_path = create_backup(switches_file)
        
        # Update specific switches
        logging.info("Updating specific switch models...")
        switches_data, updates_made = update_specific_switches(switches_data)
        
        # Add port categorization
        logging.info("Adding port categorization for N2000 series...")
        switches_data = add_port_categorization(switches_data)
        
        # Save updated data
        logging.info(f"Saving updated data to {switches_file}...")
        with open(switches_file, 'w', encoding='utf-8') as f:
            json.dump(switches_data, f, indent=2, ensure_ascii=False)
        
        # Generate and save report
        report = generate_update_report(updates_made, backup_path)
        report_file = f"switch_update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Display report
        print("\n" + report)
        logging.info(f"Update report saved to: {report_file}")
        logging.info("Switch model updates completed successfully!")
        
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON file: {e}")
    except Exception as e:
        logging.error(f"Error during update process: {e}")

if __name__ == "__main__":
    main()
