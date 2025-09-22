#!/usr/bin/env python3
"""
Debug tool to analyze bulk port status parsing issues

This tool will help us understand why certain ports are showing as 
"status unclear from bulk parse" by examining the raw output format.
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from app.core.vlan_manager import VLANManager
from app.core.database import db, Switch
from app.main import create_app
from dotenv import load_dotenv

def debug_bulk_parsing():
    """Debug the bulk parsing issue by examining raw switch output"""
    
    load_dotenv()
    
    # Create Flask app context for database access
    app = create_app()
    
    with app.app_context():
        # Get the switch that was being tested (looks like switch ID that connects to 10.100.0.15)
        switches = Switch.query.filter(Switch.ip_address == '10.100.0.15').all()
        if not switches:
            print("❌ Switch 10.100.0.15 not found in database")
            return
            
        switch = switches[0]
        print(f"🔍 Debugging switch: {switch.name} ({switch.ip_address}) - Model: {switch.model}")
        
        # Get switch credentials
        switch_username = os.getenv('SWITCH_USERNAME')
        switch_password = os.getenv('SWITCH_PASSWORD')
        
        if not switch_username or not switch_password:
            print("❌ Switch credentials not found in environment variables")
            return
        
        # Initialize VLAN manager
        vlan_manager = VLANManager(
            switch.ip_address,
            switch_username,
            switch_password,
            switch.model
        )
        
        print(f"🔌 Connecting to switch...")
        if not vlan_manager.connect():
            print("❌ Failed to connect to switch")
            return
        
        try:
            # Test the problematic ports from the logs
            problematic_ports = [
                'Gi4/0/1', 'Gi4/0/2', 'Gi4/0/3', 'Gi4/0/4', 'Gi4/0/5',
                'Gi6/0/3', 'Gi6/0/5', 'Gi6/0/7', 'Gi6/0/9', 'Gi6/0/11'
            ]
            
            print(f"\n📋 Testing bulk status parsing for {len(problematic_ports)} problematic ports...")
            
            # Get raw bulk output
            print("🔍 Executing 'show interfaces status' command...")
            raw_output = vlan_manager.execute_command("show interfaces status", wait_time=1.5, expect_large_output=True)
            
            print(f"📊 Raw output length: {len(raw_output)} characters")
            print(f"📊 Raw output lines: {len(raw_output.split(chr(10)))}")
            
            # Find lines for our problematic ports
            lines = raw_output.split('\n')
            found_lines = {}
            
            for line_idx, line in enumerate(lines):
                for port in problematic_ports:
                    if port.lower() in line.lower():
                        found_lines[port] = {
                            'line_number': line_idx,
                            'raw_line': line.strip(),
                            'line_length': len(line.strip())
                        }
            
            print(f"\n📋 Found {len(found_lines)} problematic port lines:")
            print("="*80)
            
            for port, info in found_lines.items():
                print(f"Port: {port}")
                print(f"Line {info['line_number']}: '{info['raw_line']}'")
                print(f"Length: {info['line_length']} chars")
                
                # Test parsing this specific line
                parsed = vlan_manager._parse_bulk_status_line(info['raw_line'])
                if parsed:
                    print(f"✅ Parsed: {parsed['status']}, {parsed['mode']}, VLAN {parsed['current_vlan']}")
                else:
                    print(f"❌ Failed to parse")
                
                # Compare with individual port status
                try:
                    individual = vlan_manager.get_port_status(port)
                    print(f"🔍 Individual: {individual['status']}, {individual['mode']}, VLAN {individual['current_vlan']}")
                except Exception as e:
                    print(f"❌ Individual failed: {e}")
                
                print("-" * 40)
            
            # Also show a sample of good parsing ports for comparison
            print("\n📋 Sample of successfully parsed ports for comparison:")
            good_ports = ['Gi2/0/35', 'Gi2/0/36', 'Gi3/0/1', 'Gi3/0/2']
            
            for line_idx, line in enumerate(lines):
                for port in good_ports:
                    if port.lower() in line.lower():
                        print(f"Good Port {port} (Line {line_idx}): '{line.strip()}'")
                        parsed = vlan_manager._parse_bulk_status_line(line.strip())
                        if parsed:
                            print(f"✅ Parsed: {parsed['status']}, {parsed['mode']}, VLAN {parsed['current_vlan']}")
                        break
                        
        except Exception as e:
            print(f"❌ Error during debugging: {e}")
        finally:
            vlan_manager.disconnect()
            print("🔌 Disconnected from switch")

if __name__ == '__main__':
    debug_bulk_parsing()
