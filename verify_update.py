#!/usr/bin/env python3
"""
Simple verification script to check updated switch
"""

import json

def main():
    with open('switches.json', 'r') as f:
        data = json.load(f)
    
    # Find CEBU-F18-R2-DAS-01
    for site_name, site_data in data['sites'].items():
        if 'floors' in site_data:
            for floor_name, floor_data in site_data['floors'].items():
                if 'switches' in floor_data:
                    for switch_name, switch_data in floor_data['switches'].items():
                        if switch_name == 'CEBU-F18-R2-DAS-01':
                            print(f"Switch: {switch_name}")
                            print(f"Model: {switch_data['model']}")
                            print(f"Series: {switch_data['series']}")
                            print(f"Port Category: {switch_data['port_category']}")
                            print(f"IP Address: {switch_data['ip_address']}")
                            return
    print("Switch not found")

if __name__ == "__main__":
    main()
