#!/usr/bin/env python3
import json

def count_switches():
    try:
        with open('switches.json', 'r') as f:
            data = json.load(f)
        
        sites = data.get('sites', {})
        total_switches = 0
        site_count = 0
        
        print("=== LOCAL SWITCHES.JSON ANALYSIS ===")
        print(f"Total Sites: {len(sites)}")
        print()
        
        for site_name, site_data in sites.items():
            site_count += 1
            floors = site_data.get('floors', {})
            site_switches = 0
            
            for floor_name, floor_data in floors.items():
                switches = floor_data.get('switches', {})
                site_switches += len(switches)
                total_switches += len(switches)
            
            print(f"{site_count:2d}. {site_name}: {site_switches} switches")
        
        print()
        print(f"TOTAL: {len(sites)} sites, {total_switches} switches")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    count_switches()
