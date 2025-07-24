#!/usr/bin/env python3
"""
Script to update series information based on updated models
"""

import json

def main():
    # Load current switches.json
    with open('switches.json', 'r') as f:
        switches_data = json.load(f)
    
    # Model to series mapping
    model_series_mapping = {
        'Dell N2048': {'series': 'N2000', 'port_category': 'gi_te_ports'},
        'Dell N3000': {'series': 'N3000', 'port_category': 'gi_te_ports'},
        'Dell N3248': {'series': 'N3200', 'port_category': 'te_tw_ports'},
        'Dell N1548': {'series': 'N1500', 'port_category': 'gi_ports'},
        'Dell N1548P': {'series': 'N1500', 'port_category': 'gi_ports'},
    }
    
    updates_made = 0
    
    print("=" * 60)
    print("UPDATING SERIES AND PORT CATEGORY INFORMATION")
    print("=" * 60)
    print()
    
    # Update series for each switch based on model
    for site_name, site_data in switches_data['sites'].items():
        if 'floors' in site_data:
            for floor_name, floor_data in site_data['floors'].items():
                if 'switches' in floor_data:
                    for switch_name, switch_data in floor_data['switches'].items():
                        model = switch_data['model']
                        if model in model_series_mapping:
                            expected_series = model_series_mapping[model]['series']
                            expected_port_category = model_series_mapping[model]['port_category']
                            
                            current_series = switch_data.get('series', 'Unknown')
                            current_port_category = switch_data.get('port_category', 'Unknown')
                            
                            # Update series if different
                            if current_series != expected_series:
                                switch_data['series'] = expected_series
                                updates_made += 1
                                print(f"✓ Updated {switch_name} series: {current_series} → {expected_series}")
                            
                            # Update port_category if different
                            if current_port_category != expected_port_category:
                                switch_data['port_category'] = expected_port_category
                                print(f"  - Updated {switch_name} port_category: {current_port_category} → {expected_port_category}")
    
    print()
    print(f"Total series updates made: {updates_made}")
    
    # Save updated switches.json
    with open('switches.json', 'w') as f:
        json.dump(switches_data, f, indent=2)
    
    print("✓ Series information updated successfully!")
    
    # Show final summary
    print()
    print("SERIES DISTRIBUTION AFTER UPDATES:")
    print("-" * 40)
    
    series_count = {}
    for site_name, site_data in switches_data['sites'].items():
        if 'floors' in site_data:
            for floor_name, floor_data in site_data['floors'].items():
                if 'switches' in floor_data:
                    for switch_name, switch_data in floor_data['switches'].items():
                        series = switch_data.get('series', 'Unknown')
                        series_count[series] = series_count.get(series, 0) + 1
    
    for series, count in sorted(series_count.items()):
        print(f"{series}: {count} switches")

if __name__ == "__main__":
    main()
