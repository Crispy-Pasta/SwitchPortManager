#!/usr/bin/env python3
"""
Test script to reproduce the port status parsing bug.
This demonstrates the issue where ports show as "Up" when they're actually "Down".
"""

import sys
import os
import re

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_parse_bulk_status_line(line):
    """
    Test version of the _parse_bulk_status_line method to demonstrate the bug.
    """
    try:
        line = line.strip()
        if not line:
            return None
        
        # Split by multiple whitespace or tabs to handle variable spacing
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
        
        # Extract description if present
        if len(columns) > 1:
            description = columns[1].strip()
        
        # Parse status information from remaining columns
        link_state_found = False
        
        for i, col in enumerate(columns):
            col_stripped = col.strip()
            col_lower = col_stripped.lower()
            
            # Look for link state
            if col_lower in ['up', 'connected'] and not link_state_found:
                port_up = True
                link_state_found = True
                print(f"  → Found explicit UP state: '{col_stripped}'")
            elif col_lower in ['down', 'notconnect', 'disabled', 'disable'] and not link_state_found:
                port_up = False
                link_state_found = True
                print(f"  → Found explicit DOWN state: '{col_stripped}'")
        
        # THIS IS THE PROBLEMATIC HEURISTIC FALLBACK:
        if not link_state_found:
            print(f"  → No explicit link state found, using heuristic...")
            # Look for speed and duplex indicators
            has_speed_duplex = any(
                re.match(r'^(10|100|1000|10000)$', col.strip()) or 
                col.strip().lower() in ['full', 'half']
                for col in columns
            )
            
            speed_duplex_found = [col.strip() for col in columns 
                                if re.match(r'^(10|100|1000|10000)$', col.strip()) or 
                                   col.strip().lower() in ['full', 'half']]
            
            print(f"  → Speed/duplex indicators found: {speed_duplex_found}")
            print(f"  → has_speed_duplex: {has_speed_duplex}")
            
            # BUG: If we have speed/duplex info, assume UP; otherwise assume DOWN
            port_up = has_speed_duplex  # ← THIS IS WRONG!
            print(f"  → HEURISTIC RESULT: port_up = {port_up} (BUG!)")
        
        return {
            'port': port_name,
            'status': 'up' if port_up else 'down',
            'mode': port_mode,
            'current_vlan': current_vlan,
            'description': description,
            'raw_line': line,
            'link_state_found': link_state_found
        }
        
    except Exception as e:
        print(f"Failed to parse bulk status line '{line}': {str(e)}")
        return None

def main():
    print("🐛 REPRODUCING PORT STATUS PARSING BUG")
    print("=" * 60)
    
    # Test cases with typical Dell switch output
    test_cases = [
        # Case 1: Port that's actually UP (should work correctly)
        {
            'name': 'Port Actually UP',
            'line': 'Gi3/0/24  PC-Room-Wall-24     Full   1000    Auto Up      On    A  123',
            'expected': 'up'
        },
        
        # Case 2: Port that's DOWN but shows speed/duplex (BUG CASE!)
        {
            'name': 'Port Actually DOWN (with speed/duplex)',
            'line': 'Gi3/0/25  Unused-Port         Full   1000    Auto Down    On    A  1',
            'expected': 'down'
        },
        
        # Case 3: Port that's DOWN with "notconnect" 
        {
            'name': 'Port DOWN (notconnect)',
            'line': 'Gi3/0/26  Empty-Port          Full   1000    Auto notconnect On A 1',
            'expected': 'down'
        },
        
        # Case 4: Port with no speed/duplex info (should be DOWN)
        {
            'name': 'Port with no speed info',
            'line': 'Gi3/0/27  Disabled-Port       N/A    N/A     N/A  Down    Off   A  1',
            'expected': 'down'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test_case['name']}")
        print(f"Input:    {test_case['line']}")
        print(f"Expected: {test_case['expected']}")
        
        result = test_parse_bulk_status_line(test_case['line'])
        
        if result:
            actual = result['status']
            print(f"Actual:   {actual}")
            
            if actual == test_case['expected']:
                print("✅ PASS")
            else:
                print(f"❌ FAIL - Expected '{test_case['expected']}' but got '{actual}'")
                if not result.get('link_state_found', True):
                    print("   ↳ This failed because of the heuristic fallback bug!")
        else:
            print("❌ FAIL - Could not parse line")
        
        print("-" * 50)
    
    print("\n🔧 SUMMARY:")
    print("The bug is in the heuristic fallback logic that assumes ports are UP")
    print("if they have speed/duplex information, but Dell switches show this")
    print("info even for DOWN ports!")

if __name__ == "__main__":
    main()
