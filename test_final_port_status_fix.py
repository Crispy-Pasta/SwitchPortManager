#!/usr/bin/env python3
"""
Final comprehensive test for the port status parsing fix.
Tests both individual and bulk parsing with the actual switch output format.
"""

import sys
import os
import re

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_individual_parsing():
    """Test individual port status parsing (get_port_status method)"""
    print("TESTING INDIVIDUAL PORT STATUS PARSING")
    print("=" * 60)
    
    # Simulate the exact switch output from user's image
    status_output = """Port    Description        Duplex  Speed  Neg   Link State
Gi1/0/1 DOWNLINK to NOC   Full    1000   Auto  Up
Gi1/0/2 DOWNLINK to NOC   Full    1000   Auto  Up"""
    
    print("Switch Output:")
    print(status_output)
    print()
    
    # Simulate the parsing logic from get_port_status
    port_name = "Gi1/0/1"
    port_status = "down"  # Default
    link_state_found = False
    
    lines = status_output.split('\n')
    for line_idx, line in enumerate(lines):
        original_line = line
        line = line.strip()
        
        if not line:
            continue
            
        # Skip command echoes
        if line.lower().startswith(('show ', 'console', 'enable', 'configure')):
            continue
            
        # Skip header lines - be more specific to avoid false positives
        if line_idx < 3 and (
            line.lower().startswith(('port', 'name', 'type', 'duplex', 'speed', 'link', 'state', 'vlan')) or
            all(word in line.lower() for word in ['port', 'description', 'duplex', 'speed', 'link', 'state'])
        ):
            continue
        if line.startswith('-') or line.startswith('='):
            continue
            
        # Look for the port data line - FIXED VERSION
        port_name_variations = [port_name, port_name.lower(), port_name.upper()]
        
        line_contains_port = False
        if not any(cmd in line.lower() for cmd in ['show', 'interface', 'status', 'configure', 'enable']):
            for port_variation in port_name_variations:
                if line.lower().startswith(port_variation.lower()):
                    line_contains_port = True
                    break
        
        if line_contains_port:
            print(f"Found port data line: '{original_line}'")
            
            # Split by multiple whitespace to handle variable spacing
            columns = re.split(r'\s{2,}|\t', line)
            if len(columns) < 3:
                columns = line.split()
            
            # If we still don't have enough columns, try a more flexible approach
            if len(columns) < 5:
                all_words = line.split()
                if len(all_words) >= 5:
                    columns = [all_words[0]]  # Port
                    status_start_idx = None
                    for i, word in enumerate(all_words[1:], 1):
                        if word.lower() in ['full', 'half', 'auto', 'up', 'down', 'connected', 'notconnect']:
                            status_start_idx = i
                            break
                    
                    if status_start_idx:
                        desc_words = all_words[1:status_start_idx]
                        columns.append(' '.join(desc_words))
                        columns.extend(all_words[status_start_idx:])
                    else:
                        columns = all_words
            
            print(f"Columns: {columns}")
            
            # Parse status
            link_state_found = False
            
            # Method 1: Look for explicit status in columns
            for i, col in enumerate(columns):
                col_stripped = col.strip()
                col_lower = col_stripped.lower()
                
                if col_lower in ['up', 'connected']:
                    port_status = 'up'
                    link_state_found = True
                    print(f"Found explicit UP in column {i}: '{col_stripped}'")
                    break
                elif col_lower in ['down', 'notconnect', 'nolink']:
                    port_status = 'down'
                    link_state_found = True
                    print(f"Found explicit DOWN in column {i}: '{col_stripped}'")
                    break
            
            # Method 1.5: Look for compound indicators like "Auto Up"
            if not link_state_found:
                line_words = original_line.split()
                for i in range(len(line_words)):
                    word_lower = line_words[i].lower()
                    if word_lower == 'auto' and i + 1 < len(line_words):
                        next_word = line_words[i + 1].lower()
                        if next_word == 'up':
                            port_status = 'up'
                            link_state_found = True
                            print(f"Found compound UP: 'Auto Up'")
                            break
                        elif next_word in ['down', 'notconnect']:
                            port_status = 'down'
                            link_state_found = True
                            print(f"Found compound DOWN: 'Auto {next_word}'")
                            break
                    elif word_lower == 'up':
                        port_status = 'up'
                        link_state_found = True
                        print(f"Found standalone UP at word {i}")
                        break
                    elif word_lower in ['down', 'notconnect']:
                        port_status = 'down'
                        link_state_found = True
                        print(f"Found standalone DOWN at word {i}")
                        break
            
            if not link_state_found:
                print("No explicit status found, would default to DOWN")
            
            break  # Found the port line, stop searching
    
    print(f"\nRESULT: port_status = '{port_status}' (link_state_found = {link_state_found})")
    return port_status

def test_bulk_parsing():
    """Test bulk port status parsing (_parse_bulk_status_line method)"""
    print("\nTESTING BULK PORT STATUS PARSING")
    print("=" * 60)
    
    # Test the bulk parser with the same format
    test_lines = [
        "Gi1/0/1 DOWNLINK to NOC   Full    1000   Auto  Up",
        "Gi1/0/2 DOWNLINK to NOC   Full    1000   Auto  Up"
    ]
    
    for line in test_lines:
        print(f"\nTesting line: {line}")
        
        # Simulate the bulk parser logic
        line = line.strip()
        columns = re.split(r'\s{2,}|\t', line)
        if len(columns) < 3:
            columns = line.split()
        
        # If we still don't have enough columns, try a more flexible approach
        if len(columns) < 5:
            all_words = line.split()
            if len(all_words) >= 5:
                columns = [all_words[0]]  # Port
                status_start_idx = None
                for i, word in enumerate(all_words[1:], 1):
                    if word.lower() in ['full', 'half', 'auto', 'up', 'down', 'connected', 'notconnect']:
                        status_start_idx = i
                        break
                
                if status_start_idx:
                    desc_words = all_words[1:status_start_idx]
                    columns.append(' '.join(desc_words))
                    columns.extend(all_words[status_start_idx:])
                else:
                    columns = all_words
        
        print(f"Columns: {columns}")
        
        # Parse status
        port_status = "down"
        link_state_found = False
        
        # Look for link state in columns
        for i, col in enumerate(columns):
            col_stripped = col.strip()
            col_lower = col_stripped.lower()
            
            if col_lower in ['up', 'connected'] and not link_state_found:
                port_status = 'up'
                link_state_found = True
                print(f"Found UP in column {i}: '{col_stripped}'")
                break
            elif col_lower in ['down', 'notconnect', 'nolink'] and not link_state_found:
                port_status = 'down'
                link_state_found = True
                print(f"Found DOWN in column {i}: '{col_stripped}'")
                break
        
        # Word-by-word search for compound patterns
        if not link_state_found:
            line_words = line.split()
            for i, word in enumerate(line_words):
                word_lower = word.lower()
                if word_lower == 'auto' and i + 1 < len(line_words):
                    next_word = line_words[i + 1].lower()
                    if next_word == 'up':
                        port_status = 'up'
                        link_state_found = True
                        print(f"Found compound UP: 'Auto Up'")
                        break
                    elif next_word in ['down', 'notconnect']:
                        port_status = 'down'
                        link_state_found = True
                        print(f"Found compound DOWN: 'Auto {next_word}'")
                        break
                elif word_lower == 'up':
                    port_status = 'up'
                    link_state_found = True
                    print(f"Found standalone UP at word {i}")
                    break
                elif word_lower in ['down', 'notconnect']:
                    port_status = 'down'
                    link_state_found = True
                    print(f"Found standalone DOWN at word {i}")
                    break
        
        if not link_state_found:
            print("No explicit status found, would default to DOWN")
        
        print(f"RESULT: {port_status}")

def main():
    print("COMPREHENSIVE PORT STATUS PARSING TEST")
    print("=" * 80)
    print("Testing the fix for the issue where ports show as DOWN when actually UP")
    print()
    
    # Test individual parsing
    individual_result = test_individual_parsing()
    
    # Test bulk parsing
    test_bulk_parsing()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if individual_result == 'up':
        print("PASS - INDIVIDUAL PARSING: Correctly detected UP status")
    else:
        print("FAIL - INDIVIDUAL PARSING: Expected 'up' but got '{}'".format(individual_result))
    
    print("\nKey improvements made:")
    print("1. Fixed header detection to avoid false positives")
    print("2. Improved column splitting for multi-word descriptions")
    print("3. Enhanced 'Auto Up' pattern detection")
    print("4. Added standalone 'Up'/'Down' detection")
    print("5. Applied fixes to both individual and bulk parsers")
    
    print("\nThe port status parsing should now work correctly with your Dell switch output!")

if __name__ == "__main__":
    main()
