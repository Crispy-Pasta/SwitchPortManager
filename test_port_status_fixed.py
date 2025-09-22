#!/usr/bin/env python3
"""
Test script to verify the port status parsing bug fix.
This demonstrates the corrected parsing logic that properly handles DOWN ports.
"""

import sys
import os
import re

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_parse_bulk_status_line_fixed(line):
    """
    Test version of the FIXED _parse_bulk_status_line method.
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
        
        # FIXED HEURISTIC FALLBACK:
        if not link_state_found:
            print(f"  → No explicit link state found, using SAFER heuristic...")
            # CRITICAL FIX: Look for "Down", "notconnect", etc. in the text first
            line_content = line.lower()
            
            # Check for UP indicators (be precise about positioning)
            if ' up ' in line_content or line_content.endswith(' up'):
                port_up = True
                print(f"  → Found UP via text search")
            # Check for DOWN indicators (broader search as these can appear in various forms)
            elif any(down_indicator in line_content for down_indicator in 
                    [' down ', ' notconnect', ' disabled', ' nolink', 'err-disabled']):
                port_up = False
                print(f"  → Found DOWN via text search")
            else:
                # REMOVED THE BUGGY HEURISTIC: Don't assume UP based on speed/duplex
                # Dell switches show speed/duplex even for DOWN ports!
                # Always default to DOWN when status is unclear for safety
                port_up = False
                print(f"  → FIXED: Defaulting to DOWN for safety (no clear indicators found)")
        
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
    print("✅ TESTING FIXED PORT STATUS PARSING")
    print("=" * 60)
    
    # Test cases with typical Dell switch output
    test_cases = [
        # Case 1: Port that's actually UP (should work correctly)
        {
            'name': 'Port Actually UP',
            'line': 'Gi3/0/24  PC-Room-Wall-24     Full   1000    Auto Up      On    A  123',
            'expected': 'up'
        },
        
        # Case 2: Port that's DOWN but shows speed/duplex (FIXED!)
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
        },
        
        # Case 5: Ambiguous port with speed/duplex but no clear state (FIXED: should be DOWN)
        {
            'name': 'Ambiguous port (no clear up/down)',
            'line': 'Gi3/0/28  Test-Port           Full   1000    Auto         On    A  1',
            'expected': 'down'
        }
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test_case['name']}")
        print(f"Input:    {test_case['line']}")
        print(f"Expected: {test_case['expected']}")
        
        result = test_parse_bulk_status_line_fixed(test_case['line'])
        
        if result:
            actual = result['status']
            print(f"Actual:   {actual}")
            
            if actual == test_case['expected']:
                print("✅ PASS")
                passed_tests += 1
            else:
                print(f"❌ FAIL - Expected '{test_case['expected']}' but got '{actual}'")
                failed_tests += 1
        else:
            print("❌ FAIL - Could not parse line")
            failed_tests += 1
        
        print("-" * 50)
    
    print(f"\n📊 TEST RESULTS:")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! The port status parsing bug has been FIXED!")
        print("\nKey improvements:")
        print("• Removed the buggy speed/duplex heuristic that caused false positives")
        print("• Added better text-based searching for UP/DOWN indicators") 
        print("• Default to DOWN when status is unclear (safer approach)")
        print("• Enhanced logging for troubleshooting")
    else:
        print(f"\n⚠️  {failed_tests} tests still failing. Further investigation needed.")

if __name__ == "__main__":
    main()
