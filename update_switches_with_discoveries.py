#!/usr/bin/env python3
"""
Script to update switches.json with discovered model corrections
"""

import json
import os
from datetime import datetime

def main():
    # Load current switches.json
    with open('switches.json', 'r') as f:
        switches_data = json.load(f)
    
    # Model corrections discovered from SSH discovery
    model_corrections = {
        # VCORP switches - N1548/N1548P → Dell N3000
        'VCORP-F5-R4-DVAS-02': 'Dell N3000',
        'VCORP-F5-R2-DVAS-03': 'Dell N3000',
        
        # CEBU switches - Dell N3000 → Dell N2048 (most of them)
        'CEBU-F18-R2-DAS-01': 'Dell N2048',
        'CEBU-F18-C2-VAS-08': 'Dell N2048',
        'CEBU-F16-C1-VAS-02': 'Dell N2048',
        'CEBU-F16-R2-VAS-03': 'Dell N2048',
        'CEBU-F16-R4-VAS-04': 'Dell N2048',
        'CEBU-F17-C1-VAS-05': 'Dell N2048',
        'CEBU-F17-R2-VAS-06': 'Dell N2048',
        'CEBU-F17-R4-VAS-07': 'Dell N2048',
        'CEBU-F10-C1-VAS-09': 'Dell N2048',
        'CEBU-F10-C1-VAS-10': 'Dell N2048',
        
        # One CEBU switch - Dell N3000 → Dell N3248
        'CEBU-F17-R1-AS-01': 'Dell N3248',
        
        # CEBUHM switches - Dell N3000 → Dell N2048
        'CEBUHM-F15-C1-VAS-01': 'Dell N2048',
        'CEBUHM-F15-C1-VAS-02': 'Dell N2048',
        
        # AXIS switches - Dell N3000 → Dell N2048
        'AXIS-F24-R1-AS-01': 'Dell N2048',
        'AXIS-F24-R2-AS-02': 'Dell N2048',
        'AXIS-26F-R1-AS-03': 'Dell N2048',
        'AXIS-26F-R2-AS-04': 'Dell N2048',
        
        # Uptown switches - Dell N3000 → Dell N2048
        'UPT-F19-R2-VAS-01': 'Dell N2048',
        'UPT-F19-R3-VAS-02': 'Dell N2048',
        'UPT-F19-R2-VAS-03': 'Dell N2048',
        'UPT-F19-R3-VAS-04': 'Dell N2048',
        'UPT-F19-C1-DAS-01': 'Dell N2048',
        'UPT-F20-C2-VAS-06': 'Dell N2048',
        'UPT-F20-R1-VAS-07': 'Dell N2048',
        'UPT-F20-R3-DVAS-01': 'Dell N2048',
        'UPT-F20-R2-VAS-08': 'Dell N2048',
        'UPT-F20-R4-DVAS-02': 'Dell N2048',
        
        # Cyber Sigma switches - Dell N3000 → Dell N2048
        'SIGMA-S20-R2-AS-01': 'Dell N2048',
        'SIGMA-F20-R4-VAS-02': 'Dell N2048',
        'SIGMA-F20-R6HUB-AS-03': 'Dell N2048',
        'SIGMA-F19-R2-VAS-05': 'Dell N2048',
        'SIGMA-F19-R4-VAS-06': 'Dell N2048',
        'SIGMA-F19-R6HUB-VAS-07': 'Dell N2048',
        
        # 5ECOM switches - Dell N3000 → Dell N2048
        '5ECOM-F12-C2-VAS-01': 'Dell N2048',
    }
    
    updates_made = 0
    
    print("=" * 60)
    print("UPDATING SWITCHES.JSON WITH DISCOVERED MODEL CORRECTIONS")
    print("=" * 60)
    print(f"Applying {len(model_corrections)} model corrections...")
    print()
    
    # Apply corrections to each site
    for site_name, site_data in switches_data['sites'].items():
        if 'floors' in site_data:
            for floor_name, floor_data in site_data['floors'].items():
                if 'switches' in floor_data:
                    for switch_name, switch_data in floor_data['switches'].items():
                        if switch_name in model_corrections:
                            old_model = switch_data['model']
                            new_model = model_corrections[switch_name]
                            switch_data['model'] = new_model
                            updates_made += 1
                            print(f"✓ Updated {switch_name}: {old_model} → {new_model}")
    
    print()
    print(f"Total updates made: {updates_made}")
    
    # Create backup of original file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"switches_backup_{timestamp}.json"
    
    with open('switches.json', 'r') as f:
        original_data = f.read()
    
    with open(backup_filename, 'w') as f:
        f.write(original_data)
    
    print(f"Backup created: {backup_filename}")
    
    # Save updated switches.json
    with open('switches.json', 'w') as f:
        json.dump(switches_data, f, indent=2)
    
    print("✓ switches.json updated successfully!")
    
    # Show summary of changes by model type
    print()
    print("SUMMARY OF MODEL CORRECTIONS:")
    print("-" * 40)
    
    n3000_to_n2048 = sum(1 for model in model_corrections.values() if model == 'Dell N2048')
    n3000_to_n3248 = sum(1 for model in model_corrections.values() if model == 'Dell N3248')
    to_n3000 = sum(1 for model in model_corrections.values() if model == 'Dell N3000')
    
    print(f"Dell N3000 → Dell N2048: {n3000_to_n2048} switches")
    print(f"Dell N3000 → Dell N3248: {n3000_to_n3248} switches")  
    print(f"N1548/N1548P → Dell N3000: {to_n3000} switches")
    
    print()
    print("All model corrections have been applied!")
    print("The switches.json file now reflects the actual device models discovered via SSH.")

if __name__ == "__main__":
    main()
