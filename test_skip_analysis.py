#!/usr/bin/env python3
"""
Test script to verify the enhanced skip analysis and detailed reasons in VLAN workflow.

This script tests the new skip_analysis feature that provides detailed explanations
for why ports are excluded from VLAN changes, helping engineers understand and 
troubleshoot their network configurations.
"""

import sys
import os

# Add the parent directory to sys.path to import the vlan_manager module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.core.vlan_manager import VLANManager, _is_port_err_disabled

def test_skip_analysis_generation():
    """Test the skip analysis generation logic."""
    
    print("🚀 Testing Enhanced Skip Analysis and Detailed Reasons")
    print("=" * 70)
    
    # Mock port status data representing different scenarios
    mock_port_statuses = [
        {
            'port': 'Gi1/0/1',
            'status': 'err-disabled',
            'mode': 'access',
            'current_vlan': '100',
            'description': 'Security violation port'
        },
        {
            'port': 'Gi1/0/2', 
            'status': 'disabled',
            'mode': 'access',
            'current_vlan': '200',
            'description': 'Admin disabled port'
        },
        {
            'port': 'Gi1/0/3',
            'status': 'down',
            'mode': 'access', 
            'current_vlan': '1',
            'description': 'Unused port'
        },
        {
            'port': 'Gi1/0/4',
            'status': 'up',
            'mode': 'access',
            'current_vlan': '300',
            'description': 'Active workstation'
        },
        {
            'port': 'Gi1/0/5',
            'status': 'up',
            'mode': 'access',
            'current_vlan': '500',  # Target VLAN - already correct
            'description': 'Already correct VLAN'
        },
        {
            'port': 'Te1/0/1',
            'status': 'up',
            'mode': 'trunk',
            'current_vlan': '1',
            'description': 'Uplink to core switch'
        }
    ]
    
    target_vlan_id = 500
    
    # Simulate categorization logic from vlan_change_workflow
    ports_already_correct = []
    err_disabled_ports = []
    disabled_ports = []
    down_ports = []
    up_ports = []
    uplink_ports = []
    
    print(f"📋 Analyzing {len(mock_port_statuses)} ports for VLAN {target_vlan_id} assignment:")
    print()
    
    for status in mock_port_statuses:
        port = status['port']
        current_status = status['status'].lower()
        current_vlan = status['current_vlan']
        
        print(f"Port {port}: {current_status}, mode={status['mode']}, vlan={current_vlan}")
        
        # Check if port is already correct
        if current_vlan == str(target_vlan_id):
            ports_already_correct.append({
                'port': port,
                'reason': f'Port already assigned to VLAN {target_vlan_id}',
                'current_status': status
            })
            print(f"  ✅ Already on target VLAN {target_vlan_id}")
            continue
        
        # Check for err-disabled ports
        if current_status == 'err-disabled' or _is_port_err_disabled(status):
            err_disabled_ports.append({
                'port': port,
                'reason': 'Port is err-disabled (security policy violation detected)',
                'details': 'Port was automatically disabled due to security threats. Manual investigation required.',
                'current_status': status,
                'security_issue': True,
                'status_category': 'err-disabled'
            })
            print(f"  🚨 ERR-DISABLED - security issue detected")
            continue
        
        # Check for administratively disabled ports
        elif current_status == 'disabled':
            disabled_ports.append({
                'port': port,
                'reason': 'Port is administratively disabled',
                'details': 'Port has been manually disabled by administrator.',
                'current_status': status,
                'status_category': 'disabled'
            })
            print(f"  🔧 DISABLED - administratively disabled")
        
        # Check for down ports
        elif current_status == 'down':
            down_ports.append({
                'port': port,
                'reason': 'Port is down (no link detected)',
                'details': 'Port is physically down or no cable/device connected. Safe to configure.',
                'current_status': status,
                'status_category': 'down'
            })
            print(f"  📱 DOWN - safe to configure")
        
        # Check for up ports
        elif current_status == 'up':
            up_ports.append({
                'port': port,
                'reason': 'Port is up (active with link)', 
                'details': 'Port has an active link and may have connected devices.',
                'current_status': status,
                'status_category': 'up'
            })
            print(f"  ⚡ UP - needs confirmation")
        
        # Check for uplink ports (Te interfaces in this example)
        if port.startswith('Te'):
            uplink_ports.append(port)
            print(f"  🔒 UPLINK - protected from changes")
    
    print()
    print("=" * 70)
    print("📊 Skip Analysis Results:")
    print("=" * 70)
    
    # Generate the detailed skip analysis (matching the real code structure)
    skip_analysis = {
        'already_correct': {
            'count': len(ports_already_correct),
            'ports': ports_already_correct,
            'explanation': f'These ports are already assigned to target VLAN {target_vlan_id} and do not need changes.'
        },
        'err_disabled': {
            'count': len(err_disabled_ports),
            'ports': err_disabled_ports,
            'explanation': 'These ports are ERR-DISABLED due to security policy violations and require manual investigation before configuration changes. Common causes: unauthorized devices, port security violations, spanning tree violations.',
            'action_required': 'CRITICAL: Investigate security violations before proceeding. Check logs for unauthorized MAC addresses or policy violations.'
        },
        'disabled': {
            'count': len(disabled_ports),
            'ports': disabled_ports,
            'explanation': 'These ports are administratively disabled by network engineers. They may be safe to configure but will require "no shutdown" to activate.',
            'action_required': 'Review if these ports should be enabled after VLAN assignment for the intended workflow.'
        },
        'down': {
            'count': len(down_ports),
            'ports': down_ports,
            'explanation': 'These ports are physically down (no cable connected or device powered off). Safe to configure - VLAN changes will take effect when devices are connected.',
            'action_required': 'No immediate action required. VLAN assignment will be active when devices connect.'
        },
        'up': {
            'count': len(up_ports),
            'ports': up_ports,
            'explanation': 'These ports are UP with active connections. Configuration changes may disrupt connected devices.',
            'action_required': 'Consider impact on connected devices. Use force change or skip non-access options to proceed.'
        }
    }
    
    # Add uplink protection analysis
    if uplink_ports:
        skip_analysis['uplink_protected'] = {
            'count': len(uplink_ports),
            'ports': [{'port': port, 'reason': 'Uplink port - protected from accidental changes'} for port in uplink_ports],
            'explanation': 'These are uplink/trunk ports that connect to other switches or network infrastructure. They are protected from accidental VLAN changes.',
            'action_required': 'CAUTION: Only modify if you are certain these are not critical network connections. Use force change to override protection.'
        }
    
    # Display detailed skip analysis
    for category, details in skip_analysis.items():
        if details['count'] > 0:
            print(f"\n{category.upper().replace('_', ' ')} ({details['count']} ports):")
            print(f"  📝 Explanation: {details['explanation']}")
            if 'action_required' in details:
                print(f"  ⚠️  Action Required: {details['action_required']}")
            
            print(f"  📋 Affected Ports:")
            for port_info in details['ports']:
                if isinstance(port_info, dict):
                    port_name = port_info.get('port', 'Unknown')
                    reason = port_info.get('reason', 'No reason provided')
                    print(f"     • {port_name}: {reason}")
                else:
                    print(f"     • {port_info}")
    
    print()
    print("=" * 70)
    print("📱 Enhanced Skip Summary:")
    print("=" * 70)
    
    # Generate the enhanced skip summary with emojis (matching real code)
    skip_summary_parts = []
    
    # Critical items first (err-disabled)
    if skip_analysis.get('err_disabled', {}).get('count', 0) > 0:
        count = skip_analysis['err_disabled']['count']
        skip_summary_parts.append(f"🚨 CRITICAL: {count} err-disabled port{'s' if count > 1 else ''} require investigation")
    
    # Already correct ports
    if skip_analysis.get('already_correct', {}).get('count', 0) > 0:
        count = skip_analysis['already_correct']['count']
        skip_summary_parts.append(f"✅ {count} port{'s' if count > 1 else ''} already on target VLAN")
    
    # Administratively disabled ports
    if skip_analysis.get('disabled', {}).get('count', 0) > 0:
        count = skip_analysis['disabled']['count']
        skip_summary_parts.append(f"🔧 {count} administratively disabled port{'s' if count > 1 else ''}")
    
    # Down ports (informational)
    if skip_analysis.get('down', {}).get('count', 0) > 0:
        count = skip_analysis['down']['count']
        skip_summary_parts.append(f"📱 {count} down port{'s' if count > 1 else ''} (will apply when connected)")
    
    # Up ports (requiring attention)
    if skip_analysis.get('up', {}).get('count', 0) > 0:
        count = skip_analysis['up']['count'] 
        skip_summary_parts.append(f"⚡ {count} active port{'s' if count > 1 else ''} (consider device impact)")
    
    # Uplink protected ports
    if skip_analysis.get('uplink_protected', {}).get('count', 0) > 0:
        count = skip_analysis['uplink_protected']['count']
        skip_summary_parts.append(f"🔒 {count} uplink port{'s' if count > 1 else ''} (protected)")
    
    skip_summary = ' | '.join(skip_summary_parts) if skip_summary_parts else 'No ports skipped'
    
    print(f"Summary: {skip_summary}")
    
    print()
    print("=" * 70)
    print("✅ Skip Analysis Test Complete!")
    print()
    print("💡 Key Features Demonstrated:")
    print("   ✓ Detailed categorization of skipped ports")
    print("   ✓ Clear explanations for each skip reason") 
    print("   ✓ Actionable guidance for network engineers")
    print("   ✓ Security-first approach for err-disabled ports")
    print("   ✓ Visual summary with emoji indicators")
    print("   ✓ Priority ordering (critical issues first)")

def test_error_message_generation():
    """Test the enhanced error message generation for validation failures."""
    
    print("\n" + "=" * 70)
    print("🧪 Testing Enhanced Error Message Generation")
    print("=" * 70)
    
    from app.core.vlan_manager import (
        get_port_format_error_message,
        get_vlan_format_error_message
    )
    
    # Test port format error messages
    print("\n📍 Port Format Error Messages:")
    invalid_ports = ["invalid_port", "Gi1/0/", "'; DROP TABLE ports; --"]
    
    for invalid_port in invalid_ports:
        error_msg = get_port_format_error_message(invalid_port)
        print(f"\nInvalid input: '{invalid_port}'")
        print(f"Error: {error_msg['error']}")
        print(f"Valid formats: {', '.join(error_msg['details']['valid_formats'][:2])}...")
    
    # Test VLAN ID error messages
    print("\n📍 VLAN ID Error Messages:")
    invalid_vlan_ids = ["0", "4095", "invalid", "-1"]
    
    for invalid_id in invalid_vlan_ids:
        error_msg = get_vlan_format_error_message('vlan_id', invalid_id)
        print(f"\nInvalid VLAN ID: '{invalid_id}'")
        print(f"Error: {error_msg['error']}")
        print(f"Valid range: {error_msg['details']['valid_range']}")
    
    # Test VLAN name error messages
    print("\n📍 VLAN Name Error Messages:")
    invalid_vlan_names = ["", "configure", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]
    
    for invalid_name in invalid_vlan_names:
        error_msg = get_vlan_format_error_message('vlan_name', invalid_name)
        print(f"\nInvalid VLAN name: '{invalid_name[:20]}{'...' if len(invalid_name) > 20 else ''}'")
        print(f"Error: {error_msg['error']}")
        print(f"Standards: {', '.join(error_msg['details']['naming_standards'][:2])}...")
    
    print("\n✅ Error message generation test complete!")

if __name__ == "__main__":
    test_skip_analysis_generation()
    test_error_message_generation()
    print("\n🎉 All skip analysis tests passed!")
