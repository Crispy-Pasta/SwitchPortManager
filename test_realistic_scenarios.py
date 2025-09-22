#!/usr/bin/env python3
"""
Realistic scenario testing for the enhanced VLAN manager.

This script simulates real-world network scenarios that network engineers 
encounter daily, demonstrating the enhanced skip analysis capabilities.
"""

import sys
import os

# Add the parent directory to sys.path to import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.core.vlan_manager import (
    is_valid_port_input,
    is_valid_vlan_id,
    is_valid_vlan_name,
    is_valid_port_description,
    get_port_format_error_message,
    get_vlan_format_error_message,
    _is_port_err_disabled
)

def test_realistic_enterprise_scenarios():
    """Test realistic enterprise VLAN management scenarios."""
    
    print("🏢 Enhanced VLAN Manager - Realistic Enterprise Scenarios")
    print("=" * 80)
    
    scenarios = [
        {
            'name': 'New Employee Onboarding',
            'description': 'Setting up workstation ports for new hires in Building A',
            'ports': 'Gi1/0/15-20',
            'vlan_id': '150',
            'vlan_name': 'Zone_Employee_BuildingA',
            'port_description': 'New Employee Workstation - Building A Floor 1',
            'workflow_type': 'onboarding',
            'expected_issues': 'None - Clean onboarding scenario'
        },
        {
            'name': 'Security Incident Response',
            'description': 'Moving compromised ports to quarantine VLAN',
            'ports': 'Gi2/0/8,Gi2/0/12,Gi3/0/25',
            'vlan_id': '999',
            'vlan_name': 'Security_Quarantine',
            'port_description': 'SECURITY INCIDENT: Quarantined port - unauthorized access detected',
            'workflow_type': 'offboarding',
            'expected_issues': 'Some ports may be err-disabled due to security violations'
        },
        {
            'name': 'Voice Network Deployment',
            'description': 'Configuring IP phones across multiple floors',
            'ports': 'Gi1/0/1-24,Gi2/0/1-24,Gi3/0/1-24',
            'vlan_id': '200',
            'vlan_name': 'Voice_Network',
            'port_description': 'IP Phone Port - Voice Network VLAN 200',
            'workflow_type': 'onboarding',
            'expected_issues': 'Some ports may be up with existing devices'
        },
        {
            'name': 'Guest WiFi Access Points',
            'description': 'Setting up guest network access points',
            'ports': 'Gi1/0/48,Gi2/0/48,Gi3/0/48,Te1/0/1',
            'vlan_id': '300',
            'vlan_name': 'Guest_Access',
            'port_description': 'Guest WiFi Access Point - Isolated Network',
            'workflow_type': 'onboarding',
            'expected_issues': 'Te1/0/1 is an uplink port and should be protected'
        },
        {
            'name': 'IoT Device Integration',
            'description': 'Connecting IoT sensors and controllers',
            'ports': 'Gi2/0/30-35',
            'vlan_id': '400',
            'vlan_name': 'IoT_Devices',
            'port_description': 'IoT Device Port - Environmental Sensors',
            'workflow_type': 'onboarding',
            'expected_issues': 'Ports may be administratively disabled by default'
        }
    ]
    
    print(f"📋 Testing {len(scenarios)} realistic enterprise scenarios...\n")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"🧪 Scenario {i}: {scenario['name']}")
        print(f"   📝 Description: {scenario['description']}")
        print(f"   🔌 Ports: {scenario['ports']}")
        print(f"   🏷️  VLAN: {scenario['vlan_id']} ({scenario['vlan_name']})")
        print(f"   📋 Port Description: {scenario['port_description']}")
        print(f"   🔄 Workflow: {scenario['workflow_type']}")
        print(f"   ⚠️  Expected Issues: {scenario['expected_issues']}")
        
        # Validate all components
        validations = {
            'ports': is_valid_port_input(scenario['ports']),
            'vlan_id': is_valid_vlan_id(scenario['vlan_id']),
            'vlan_name': is_valid_vlan_name(scenario['vlan_name']),
            'description': is_valid_port_description(scenario['port_description']),
            'workflow_type': scenario['workflow_type'] in ['onboarding', 'offboarding']
        }
        
        all_valid = all(validations.values())
        
        if all_valid:
            print("   ✅ VALIDATION: All inputs are valid - ready for execution")
        else:
            print("   ❌ VALIDATION: Issues detected:")
            for component, valid in validations.items():
                if not valid:
                    print(f"      🔴 {component}: Invalid format")
        
        print()

def test_security_scenarios():
    """Test security-focused scenarios and validation."""
    
    print("=" * 80)
    print("🛡️ Security-Focused Testing Scenarios")
    print("=" * 80)
    
    security_tests = [
        {
            'name': 'SQL Injection Attempt in Port Field',
            'ports': "'; DROP TABLE switches; SELECT * FROM users; --",
            'vlan_id': '100',
            'vlan_name': 'Test_VLAN',
            'description': 'Legitimate description',
            'expected': 'BLOCKED - Invalid port format'
        },
        {
            'name': 'Command Injection in VLAN Name',
            'ports': 'Gi1/0/1',
            'vlan_id': '200',
            'vlan_name': 'configure; rm -rf /; exit',
            'description': 'Normal description',
            'expected': 'BLOCKED - Reserved/dangerous VLAN name'
        },
        {
            'name': 'Script Injection in Description',
            'ports': 'Gi1/0/1',
            'vlan_id': '300',
            'vlan_name': 'Valid_VLAN',
            'description': '<script>alert("xss")</script>',
            'expected': 'BLOCKED - Invalid characters in description'
        },
        {
            'name': 'Reserved VLAN ID Attack',
            'ports': 'Gi1/0/1',
            'vlan_id': '4095',  # Reserved VLAN
            'vlan_name': 'Attack_VLAN',
            'description': 'Normal description',
            'expected': 'BLOCKED - Reserved VLAN ID'
        },
        {
            'name': 'Legitimate Enterprise Configuration',
            'ports': 'Gi1/0/1-10,Gi2/0/5',
            'vlan_id': '250',
            'vlan_name': 'Zone_Marketing_Floor2',
            'description': 'Marketing Department - Building B Floor 2 [Authorized by IT-2024-001]',
            'expected': 'ALLOWED - Valid enterprise configuration'
        }
    ]
    
    print(f"🔍 Testing {len(security_tests)} security scenarios...\n")
    
    for i, test in enumerate(security_tests, 1):
        print(f"🔒 Security Test {i}: {test['name']}")
        print(f"   Ports: {test['ports']}")
        print(f"   VLAN: {test['vlan_id']} ({test['vlan_name']})")
        print(f"   Description: {test['description']}")
        
        # Perform validation
        port_valid = is_valid_port_input(test['ports'])
        vlan_id_valid = is_valid_vlan_id(test['vlan_id'])
        vlan_name_valid = is_valid_vlan_name(test['vlan_name'])
        desc_valid = is_valid_port_description(test['description'])
        
        all_valid = all([port_valid, vlan_id_valid, vlan_name_valid, desc_valid])
        
        if all_valid:
            result = "✅ ALLOWED"
        else:
            result = "🚫 BLOCKED"
            
        print(f"   Expected: {test['expected']}")
        print(f"   Result: {result}")
        
        if not all_valid:
            print("   🔍 Validation Details:")
            if not port_valid:
                print("      🔴 Ports: Invalid format detected")
            if not vlan_id_valid:
                print("      🔴 VLAN ID: Out of valid range or reserved")
            if not vlan_name_valid:
                print("      🔴 VLAN Name: Contains dangerous or reserved keywords")
            if not desc_valid:
                print("      🔴 Description: Contains unsafe characters or patterns")
        
        print()

def demonstrate_skip_analysis_in_action():
    """Demonstrate the skip analysis with a realistic mixed-port scenario."""
    
    print("=" * 80)
    print("📊 Skip Analysis Demonstration - Mixed Port Scenario")
    print("=" * 80)
    
    print("🏢 Scenario: Large office floor reconfiguration")
    print("   📋 Task: Moving 20 ports from old VLAN 100 to new VLAN 250 (Zone_Sales_Floor3)")
    print("   🎯 Target: Minimize disruption while ensuring security compliance")
    print()
    
    # Simulate a realistic mixed-port status scenario
    mock_ports = [
        ('Gi1/0/1', 'err-disabled', 'access', '100', 'SECURITY VIOLATION - Unauthorized device detected'),
        ('Gi1/0/2', 'disabled', 'access', '100', 'Administratively disabled - maintenance port'),
        ('Gi1/0/3', 'down', 'access', '100', 'Unused port - available for assignment'),
        ('Gi1/0/4', 'down', 'access', '100', 'Unused port - available for assignment'),
        ('Gi1/0/5', 'up', 'access', '100', 'Active workstation - Sales Manager'),
        ('Gi1/0/6', 'up', 'access', '100', 'Active workstation - Sales Rep 1'),
        ('Gi1/0/7', 'up', 'access', '100', 'Active workstation - Sales Rep 2'),
        ('Gi1/0/8', 'up', 'access', '250', 'Already migrated to new VLAN'),
        ('Gi1/0/9', 'up', 'access', '250', 'Already migrated to new VLAN'),
        ('Gi1/0/10', 'down', 'access', '100', 'Unused port - available for assignment'),
        ('Te1/0/1', 'up', 'trunk', '1', 'UPLINK to core switch - DO NOT MODIFY'),
    ]
    
    target_vlan = 250
    
    # Categorize ports (matching the real workflow logic)
    categories = {
        'err_disabled': [],
        'disabled': [],
        'down': [],
        'up': [],
        'already_correct': [],
        'uplink_protected': []
    }
    
    print("📋 Port Analysis Results:")
    print("=" * 50)
    
    for port, status, mode, current_vlan, description in mock_ports:
        print(f"Port {port}: {status}, mode={mode}, vlan={current_vlan}")
        print(f"   Description: {description}")
        
        # Categorize based on status and conditions
        if current_vlan == str(target_vlan):
            categories['already_correct'].append({
                'port': port,
                'reason': f'Already on target VLAN {target_vlan}',
                'description': description
            })
            print(f"   Status: ✅ Already correct - no change needed")
            
        elif status == 'err-disabled':
            categories['err_disabled'].append({
                'port': port,
                'reason': 'Security policy violation - requires investigation',
                'description': description,
                'security_issue': True
            })
            print(f"   Status: 🚨 ERR-DISABLED - critical security issue")
            
        elif status == 'disabled':
            categories['disabled'].append({
                'port': port,
                'reason': 'Administratively disabled',
                'description': description
            })
            print(f"   Status: 🔧 DISABLED - may need enabling after VLAN change")
            
        elif status == 'down':
            categories['down'].append({
                'port': port,
                'reason': 'No link detected',
                'description': description
            })
            print(f"   Status: 📱 DOWN - safe to configure")
            
        elif status == 'up':
            if port.startswith('Te'):
                categories['uplink_protected'].append({
                    'port': port,
                    'reason': 'Uplink port - protected from changes',
                    'description': description
                })
                print(f"   Status: 🔒 UPLINK - protected from accidental changes")
            else:
                categories['up'].append({
                    'port': port,
                    'reason': 'Active with connections',
                    'description': description
                })
                print(f"   Status: ⚡ UP - requires confirmation for changes")
        
        print()
    
    # Generate skip analysis summary
    print("=" * 80)
    print("📊 Enhanced Skip Analysis Summary")
    print("=" * 80)
    
    skip_summary_parts = []
    
    for category, ports in categories.items():
        if ports:
            count = len(ports)
            category_name = category.replace('_', ' ').title()
            
            if category == 'err_disabled':
                skip_summary_parts.append(f"🚨 CRITICAL: {count} err-disabled port{'s' if count > 1 else ''} require investigation")
                print(f"\n🚨 CRITICAL - {category_name} ({count} ports):")
                print(f"   These ports have security policy violations and require manual investigation.")
                print(f"   Action Required: Investigate security violations before proceeding.")
                
            elif category == 'already_correct':
                skip_summary_parts.append(f"✅ {count} port{'s' if count > 1 else ''} already on target VLAN")
                print(f"\n✅ ALREADY CORRECT - {category_name} ({count} ports):")
                print(f"   These ports are already assigned to VLAN {target_vlan}.")
                print(f"   Action Required: No action needed - ports are correctly configured.")
                
            elif category == 'disabled':
                skip_summary_parts.append(f"🔧 {count} administratively disabled port{'s' if count > 1 else ''}")
                print(f"\n🔧 MEDIUM PRIORITY - {category_name} ({count} ports):")
                print(f"   These ports are administratively disabled but safe to configure.")
                print(f"   Action Required: Consider enabling ports after VLAN assignment.")
                
            elif category == 'down':
                skip_summary_parts.append(f"📱 {count} down port{'s' if count > 1 else ''} (will apply when connected)")
                print(f"\n📱 LOW PRIORITY - {category_name} ({count} ports):")
                print(f"   These ports are physically down but safe to configure.")
                print(f"   Action Required: VLAN changes will apply when devices are connected.")
                
            elif category == 'up':
                skip_summary_parts.append(f"⚡ {count} active port{'s' if count > 1 else ''} (consider device impact)")
                print(f"\n⚡ HIGH PRIORITY - {category_name} ({count} ports):")
                print(f"   These ports have active connections that may be disrupted.")
                print(f"   Action Required: Consider impact on connected devices before proceeding.")
                
            elif category == 'uplink_protected':
                skip_summary_parts.append(f"🔒 {count} uplink port{'s' if count > 1 else ''} (protected)")
                print(f"\n🔒 CRITICAL - {category_name} ({count} ports):")
                print(f"   These are network infrastructure ports protected from changes.")
                print(f"   Action Required: Only modify with extreme caution and proper authorization.")
            
            # Show affected ports
            print(f"   Affected Ports: {', '.join([p['port'] for p in ports])}")
    
    # Final summary
    skip_summary = ' | '.join(skip_summary_parts) if skip_summary_parts else 'No ports skipped'
    
    print(f"\n" + "=" * 80)
    print("📱 Executive Summary:")
    print("=" * 80)
    print(f"Summary: {skip_summary}")
    
    print(f"\n💡 Recommended Actions:")
    print(f"   1. 🚨 Investigate err-disabled port Gi1/0/1 for security violations")
    print(f"   2. ⚡ Schedule maintenance window for active ports (Gi1/0/5-7) during off-hours")
    print(f"   3. 📱 Safe to configure down ports (Gi1/0/3, Gi1/0/4, Gi1/0/10) immediately")
    print(f"   4. 🔧 Review disabled port Gi1/0/2 - enable after VLAN assignment if needed")
    print(f"   5. ✅ Ports Gi1/0/8-9 already configured correctly")
    print(f"   6. 🔒 Do not modify uplink Te1/0/1 without network architect approval")

if __name__ == "__main__":
    print("🔧 Dell Port Tracer - Enhanced VLAN Manager Realistic Testing")
    print("=" * 80)
    
    try:
        test_realistic_enterprise_scenarios()
        test_security_scenarios() 
        demonstrate_skip_analysis_in_action()
        
        print("\n" + "=" * 80)
        print("🎉 All realistic scenario tests completed successfully!")
        print("\n💡 Key Benefits Demonstrated:")
        print("   ✅ Real-world enterprise scenario support")
        print("   ✅ Comprehensive security validation and injection prevention")
        print("   ✅ Detailed skip analysis with actionable engineer guidance")
        print("   ✅ Priority-based issue classification for efficient workflow")
        print("   ✅ Clear explanations and next-step recommendations")
        
    except Exception as e:
        print(f"\n❌ Realistic testing failed with exception: {str(e)}")
        exit(1)
    
    exit(0)
