#!/usr/bin/env python3
"""
Script to extract model mismatches from discovery results
"""

import re
import json

# List to store all mismatches
mismatches = []

# Patterns to match model mismatches
mismatch_pattern = r"Model mismatch: (.+?) - Expected: (.+?), Actual: (.+)"

# Read the discovery results from previous run output
# Since the previous script ran, we'll process the output we saw
discovery_output = """
VCORP-F5-R4-DVAS-02 - Expected: Dell N1548P, Actual: Dell N3000
VCORP-F5-R2-DVAS-03 - Expected: Dell N1548, Actual: Dell N3000
CEBU-F18-R2-DAS-01 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F18-C2-VAS-08 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F16-C1-VAS-02 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F16-R2-VAS-03 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F16-R4-VAS-04 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F17-C1-VAS-05 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F17-R2-VAS-06 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F17-R4-VAS-07 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F17-R1-AS-01 - Expected: Dell N3000, Actual: Dell N3248
CEBU-F10-C1-VAS-09 - Expected: Dell N3000, Actual: Dell N2048
CEBU-F10-C1-VAS-10 - Expected: Dell N3000, Actual: Dell N2048
CEBUHM-F15-C1-VAS-01 - Expected: Dell N3000, Actual: Dell N2048
CEBUHM-F15-C1-VAS-02 - Expected: Dell N3000, Actual: Dell N2048
AXIS-F24-R1-AS-01 - Expected: Dell N3000, Actual: Dell N2048
AXIS-F24-R2-AS-02 - Expected: Dell N3000, Actual: Dell N2048
AXIS-26F-R1-AS-03 - Expected: Dell N3000, Actual: Dell N2048
AXIS-26F-R2-AS-04 - Expected: Dell N3000, Actual: Dell N2048
UPT-F19-R2-VAS-01 - Expected: Dell N3000, Actual: Dell N2048
UPT-F19-R3-VAS-02 - Expected: Dell N3000, Actual: Dell N2048
UPT-F19-R2-VAS-03 - Expected: Dell N3000, Actual: Dell N2048
UPT-F19-R3-VAS-04 - Expected: Dell N3000, Actual: Dell N2048
UPT-F19-C1-DAS-01 - Expected: Dell N3000, Actual: Dell N2048
UPT-F20-C2-VAS-06 - Expected: Dell N3000, Actual: Dell N2048
UPT-F20-R1-VAS-07 - Expected: Dell N3000, Actual: Dell N2048
UPT-F20-R3-DVAS-01 - Expected: Dell N3000, Actual: Dell N2048
UPT-F20-R2-VAS-08 - Expected: Dell N3000, Actual: Dell N2048
UPT-F20-R4-DVAS-02 - Expected: Dell N3000, Actual: Dell N2048
SIGMA-S20-R2-AS-01 - Expected: Dell N3000, Actual: Dell N2048
SIGMA-F20-R4-VAS-02 - Expected: Dell N3000, Actual: Dell N2048
SIGMA-F20-R6HUB-AS-03 - Expected: Dell N3000, Actual: Dell N2048
SIGMA-F19-R2-VAS-05 - Expected: Dell N3000, Actual: Dell N2048
SIGMA-F19-R4-VAS-06 - Expected: Dell N3000, Actual: Dell N2048
SIGMA-F19-R6HUB-VAS-07 - Expected: Dell N3000, Actual: Dell N2048
5ECOM-F12-C2-VAS-01 - Expected: Dell N3000, Actual: Dell N2048
"""

# Process each line looking for mismatch data
for line in discovery_output.strip().split('\n'):
    if line.strip():
        parts = line.split(' - Expected: ')
        if len(parts) == 2:
            switch_name = parts[0].strip()
            remaining = parts[1].split(', Actual: ')
            if len(remaining) == 2:
                expected = remaining[0].strip()
                actual = remaining[1].strip()
                
                mismatches.append({
                    'switch_name': switch_name,
                    'expected': expected,
                    'actual': actual
                })

print("=" * 60)
print("COMPREHENSIVE DELL SWITCH MODEL DISCOVERY RESULTS")
print("=" * 60)
print(f"Total mismatches found: {len(mismatches)}")
print()

# Group by expected vs actual
n3000_to_n2048 = [m for m in mismatches if m['expected'] == 'Dell N3000' and m['actual'] == 'Dell N2048']
n3000_to_n3248 = [m for m in mismatches if m['expected'] == 'Dell N3000' and m['actual'] == 'Dell N3248']
n1548_to_n3000 = [m for m in mismatches if m['expected'] in ['Dell N1548', 'Dell N1548P'] and m['actual'] == 'Dell N3000']

print("SUMMARY BY MISMATCH TYPE:")
print("-" * 40)
print(f"N3000 → N2048: {len(n3000_to_n2048)} switches")
print(f"N3000 → N3248: {len(n3000_to_n3248)} switches")  
print(f"N1548/N1548P → N3000: {len(n1548_to_n3000)} switches")
print()

print("DETAILED MISMATCHES:")
print("-" * 40)
for mismatch in mismatches:
    print(f"{mismatch['switch_name']}: {mismatch['expected']} → {mismatch['actual']}")

print()
print("SWITCHES TO UPDATE IN switches.json:")
print("-" * 40)
for mismatch in mismatches:
    print(f"  - {mismatch['switch_name']}: {mismatch['expected']} → {mismatch['actual']}")

