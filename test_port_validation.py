#!/usr/bin/env python3
"""
Test script for Dell Port Tracer VLAN Manager port validation fixes
==================================================================

This script tests the port validation functions to ensure the fix for
gi1/0/1-gi1/0/10 format works correctly.

Run this script to verify:
1. Case-insensitive port validation
2. Full range format support
3. Mixed case handling
4. Error logging improvements
"""

import sys
import os
import logging

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import the VLAN manager validation functions
from app.core.vlan_manager import (
    is_valid_port_input, 
    _is_valid_single_port, 
    _is_valid_port_number,
    VLANManager
)

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)

def test_port_validation():
    """Test various port validation scenarios."""
    
    print("=" * 60)
    print("Dell Port Tracer - Port Validation Testing")
    print("=" * 60)
    
    # Test cases with expected results
    test_cases = [
        # Full range formats (the main issue we fixed)
        ("gi1/0/1-gi1/0/10", True, "Lowercase full range"),
        ("Gi1/0/1-Gi1/0/10", True, "Uppercase full range"),  
        ("gi1/0/1-Gi1/0/10", True, "Mixed case full range"),
        ("GI1/0/1-GI1/0/10", True, "All uppercase full range"),
        
        # Short range formats (should still work)
        ("Gi1/0/1-10", True, "Short range format"),
        ("gi1/0/1-10", True, "Lowercase short range"),
        
        # Individual ports
        ("gi1/0/5", True, "Single lowercase port"),
        ("Gi1/0/5", True, "Single uppercase port"),
        ("Te1/0/1", True, "TenGig port"),
        ("te1/0/1", True, "Lowercase TenGig port"),
        ("Tw1/0/1", True, "TwentyFiveGig port"),
        ("tw1/0/1", True, "Lowercase TwentyFiveGig port"),
        
        # Multiple ports
        ("gi1/0/1,gi1/0/5,gi1/0/10", True, "Multiple lowercase ports"),
        ("Gi1/0/1,gi1/0/5,Te1/0/1", True, "Mixed case multiple ports"),
        
        # Complex combinations
        ("gi1/0/1-gi1/0/5,Gi1/0/10,Te1/0/1-2", True, "Complex mixed format"),
        
        # Invalid formats (should fail)
        ("invalid", False, "Invalid format"),
        ("gi1/0/1-gi1/0/5-gi1/0/10", False, "Too many hyphens"),
        ("gi9/0/1", False, "Invalid stack number"),
        ("gi1/5/1", False, "Invalid module number"),
        ("gi1/0/200", False, "Invalid port number"),
        ("", False, "Empty string"),
        (None, False, "None value"),
    ]
    
    print("\n1. Testing Individual Port Validation (_is_valid_single_port)")
    print("-" * 50)
    
    single_port_tests = [
        ("gi1/0/1", True),
        ("Gi1/0/1", True), 
        ("GI1/0/1", True),
        ("te1/0/1", True),
        ("Te1/0/1", True),
        ("tw1/0/1", True),
        ("Tw1/0/1", True),
        ("gi1/0/48", True),
        ("gi9/0/1", False),  # Invalid stack
        ("gi1/5/1", False),  # Invalid module
        ("gi1/0/200", False),  # Invalid port
        ("invalid", False),
    ]
    
    for port, expected in single_port_tests:
        try:
            result = _is_valid_single_port(port)
            status = "✅ PASS" if result == expected else "❌ FAIL"
            print(f"{status} | {port:<15} | Expected: {expected:<5} | Got: {result}")
        except Exception as e:
            print(f"❌ ERROR | {port:<15} | Exception: {str(e)}")
    
    print("\n2. Testing Port Range Validation (is_valid_port_input)")
    print("-" * 50)
    
    for port_input, expected, description in test_cases:
        try:
            result = is_valid_port_input(port_input)
            status = "✅ PASS" if result == expected else "❌ FAIL"
            print(f"{status} | {description:<25} | Input: {str(port_input):<20} | Expected: {expected:<5} | Got: {result}")
        except Exception as e:
            print(f"❌ ERROR | {description:<25} | Input: {str(port_input):<20} | Exception: {str(e)}")
    
    print("\n3. Testing Port Range Parsing")
    print("-" * 50)
    
    # Test the parsing functionality
    vlan_manager = VLANManager("test", "test", "test", "N3000")
    
    parse_test_cases = [
        ("gi1/0/1-gi1/0/5", ["Gi1/0/1", "Gi1/0/2", "Gi1/0/3", "Gi1/0/4", "Gi1/0/5"]),
        ("Gi1/0/1-5", ["Gi1/0/1", "Gi1/0/2", "Gi1/0/3", "Gi1/0/4", "Gi1/0/5"]),
        ("gi1/0/1,gi1/0/10", ["Gi1/0/1", "Gi1/0/10"]),
    ]
    
    for port_input, expected in parse_test_cases:
        try:
            result = vlan_manager.parse_port_range(port_input)
            status = "✅ PASS" if result == expected else "❌ FAIL"
            print(f"{status} | Input: {port_input:<20} | Expected: {expected}")
            if result != expected:
                print(f"      | Got: {result}")
        except Exception as e:
            print(f"❌ ERROR | Input: {port_input:<20} | Exception: {str(e)}")
    
    print("\n4. Testing the Original Problem Case")
    print("-" * 50)
    
    # This is the specific case that was failing before the fix
    problem_case = "gi1/0/1-gi1/0/10"
    try:
        result = is_valid_port_input(problem_case)
        if result:
            print(f"✅ SUCCESS | The original problem case '{problem_case}' now validates correctly!")
            
            # Test parsing as well
            parsed_ports = vlan_manager.parse_port_range(problem_case)
            expected_ports = [f"Gi1/0/{i}" for i in range(1, 11)]
            
            if parsed_ports == expected_ports:
                print(f"✅ SUCCESS | Parsing also works correctly: {len(parsed_ports)} ports parsed")
                print(f"           | Parsed ports: {', '.join(parsed_ports[:3])}...{parsed_ports[-1]}")
            else:
                print(f"❌ WARNING | Validation passed but parsing may have issues")
                print(f"            | Expected: {expected_ports}")
                print(f"            | Got: {parsed_ports}")
        else:
            print(f"❌ FAILED | The problem case '{problem_case}' still fails validation!")
            
    except Exception as e:
        print(f"❌ ERROR | Exception testing problem case: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("If you see ✅ SUCCESS messages above, the fix is working correctly.")
    print("=" * 60)

if __name__ == "__main__":
    test_port_validation()
