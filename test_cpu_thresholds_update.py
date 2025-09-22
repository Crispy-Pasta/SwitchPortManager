#!/usr/bin/env python3
"""
Test CPU Threshold Configuration Update
======================================

This script verifies that the CPU protection thresholds have been
successfully updated to the new, more aggressive settings.

New Thresholds:
- Green Zone: 0-75% (was 0-40%)
- Yellow Zone: 75-85% (was 40-60%) 
- Red Zone: 85-95% (was 60-80%)
- Critical Zone: 95%+ (was 80%+)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.monitoring.cpu_monitor import CPUSafetyMonitor, CPUProtectionZone

def test_default_thresholds():
    """Test that default thresholds are set to new values."""
    print("🧪 Testing CPU Monitor Default Thresholds...")
    
    # Create monitor with default values
    monitor = CPUSafetyMonitor()
    
    # Check new default thresholds
    expected_green = 75.0
    expected_yellow = 85.0
    expected_red = 95.0
    
    assert monitor.green_threshold == expected_green, f"Green threshold should be {expected_green}%, got {monitor.green_threshold}%"
    assert monitor.yellow_threshold == expected_yellow, f"Yellow threshold should be {expected_yellow}%, got {monitor.yellow_threshold}%"
    assert monitor.red_threshold == expected_red, f"Red threshold should be {expected_red}%, got {monitor.red_threshold}%"
    
    print(f"✅ Green Zone Threshold: {monitor.green_threshold}% (0-{monitor.green_threshold}%)")
    print(f"✅ Yellow Zone Threshold: {monitor.yellow_threshold}% ({monitor.green_threshold}-{monitor.yellow_threshold}%)")
    print(f"✅ Red Zone Threshold: {monitor.red_threshold}% ({monitor.yellow_threshold}-{monitor.red_threshold}%)")
    print(f"✅ Critical Zone: 95%+ (>{monitor.red_threshold}%)")

def test_protection_zone_logic():
    """Test that protection zones are determined correctly."""
    print("\n🛡️ Testing Protection Zone Logic...")
    
    monitor = CPUSafetyMonitor()
    
    # Test cases with expected zones
    test_cases = [
        (30.0, CPUProtectionZone.GREEN),    # Well within green
        (74.9, CPUProtectionZone.GREEN),   # Just under green threshold
        (75.0, CPUProtectionZone.YELLOW),  # Exactly at yellow threshold
        (80.0, CPUProtectionZone.YELLOW),  # Middle of yellow zone
        (84.9, CPUProtectionZone.YELLOW),  # Just under red threshold
        (85.0, CPUProtectionZone.RED),     # Exactly at red threshold
        (90.0, CPUProtectionZone.RED),     # Middle of red zone
        (94.9, CPUProtectionZone.RED),     # Just under critical threshold
        (95.0, CPUProtectionZone.CRITICAL), # Exactly at critical threshold
        (99.9, CPUProtectionZone.CRITICAL), # High critical load
    ]
    
    for cpu_percent, expected_zone in test_cases:
        actual_zone = monitor._determine_protection_zone(cpu_percent)
        assert actual_zone == expected_zone, f"CPU {cpu_percent}% should be in {expected_zone} zone, got {actual_zone}"
        print(f"✅ CPU {cpu_percent:5.1f}% → {actual_zone.upper()} zone")

def test_zone_limits():
    """Test that zone limits are appropriate for new thresholds."""
    print("\n👥 Testing Zone User/Worker Limits...")
    
    monitor = CPUSafetyMonitor()
    
    # Test zone limits
    zone_limits = {
        CPUProtectionZone.GREEN: (10, 8),     # Normal operation
        CPUProtectionZone.YELLOW: (6, 4),    # Reduced capacity  
        CPUProtectionZone.RED: (3, 2),       # Minimal capacity
        CPUProtectionZone.CRITICAL: (1, 1)   # Emergency only
    }
    
    for zone, (expected_users, expected_workers) in zone_limits.items():
        actual_users, actual_workers = monitor._get_zone_limits(zone)
        assert actual_users == expected_users, f"{zone} zone should allow {expected_users} users, got {actual_users}"
        assert actual_workers == expected_workers, f"{zone} zone should allow {expected_workers} workers, got {actual_workers}"
        print(f"✅ {zone.upper()} Zone: {actual_users} users, {actual_workers} workers")

def test_environment_variable_override():
    """Test that environment variables can override the new defaults."""
    print("\n🌍 Testing Environment Variable Override...")
    
    # Test with custom thresholds
    custom_monitor = CPUSafetyMonitor(
        green_threshold=70.0,
        yellow_threshold=80.0, 
        red_threshold=90.0
    )
    
    assert custom_monitor.green_threshold == 70.0
    assert custom_monitor.yellow_threshold == 80.0
    assert custom_monitor.red_threshold == 90.0
    
    print(f"✅ Custom thresholds work: {custom_monitor.green_threshold}%, {custom_monitor.yellow_threshold}%, {custom_monitor.red_threshold}%")

def main():
    """Run all threshold tests."""
    print("🚀 CPU Threshold Configuration Update Test")
    print("==========================================")
    
    try:
        test_default_thresholds()
        test_protection_zone_logic()
        test_zone_limits()
        test_environment_variable_override()
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ CPU thresholds successfully updated to more aggressive settings:")
        print("   • Green Zone: 0-75% (allows normal operation)")
        print("   • Yellow Zone: 75-85% (reduces concurrency)")
        print("   • Red Zone: 85-95% (queues requests)")
        print("   • Critical Zone: 95%+ (rejects new requests)")
        print("\n📊 System will now allow higher CPU usage before throttling.")
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)