#!/usr/bin/env python3
"""
Final Pre-Commit Test - CPU Threshold Updates
===========================================

Comprehensive test to verify all changes work before committing to repository.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_1_cpu_monitor_defaults():
    """Test 1: CPU Monitor default thresholds"""
    print("🧪 Test 1: CPU Monitor Default Thresholds")
    
    from app.monitoring.cpu_monitor import CPUSafetyMonitor
    
    monitor = CPUSafetyMonitor()
    
    # Verify new defaults
    assert monitor.green_threshold == 75.0, f"Green should be 75.0, got {monitor.green_threshold}"
    assert monitor.yellow_threshold == 85.0, f"Yellow should be 85.0, got {monitor.yellow_threshold}"
    assert monitor.red_threshold == 95.0, f"Red should be 95.0, got {monitor.red_threshold}"
    
    monitor.stop_monitoring()
    print("✅ Test 1 PASSED: Default thresholds are correct")
    return True

def test_2_zone_determination():
    """Test 2: Protection zone determination logic"""
    print("\n🧪 Test 2: Protection Zone Logic")
    
    from app.monitoring.cpu_monitor import CPUSafetyMonitor, CPUProtectionZone
    
    monitor = CPUSafetyMonitor()
    
    # Test critical transition points
    test_cases = [
        (74.9, CPUProtectionZone.GREEN),
        (75.0, CPUProtectionZone.YELLOW),
        (84.9, CPUProtectionZone.YELLOW),
        (85.0, CPUProtectionZone.RED),
        (94.9, CPUProtectionZone.RED),
        (95.0, CPUProtectionZone.CRITICAL),
    ]
    
    for cpu, expected_zone in test_cases:
        actual_zone = monitor._determine_protection_zone(cpu)
        assert actual_zone == expected_zone, f"CPU {cpu}% should be {expected_zone}, got {actual_zone}"
    
    monitor.stop_monitoring()
    print("✅ Test 2 PASSED: Protection zone logic works correctly")
    return True

def test_3_environment_overrides():
    """Test 3: Environment variable overrides"""
    print("\n🧪 Test 3: Environment Variable Overrides")
    
    # Backup original env
    backup_env = {
        'CPU_GREEN_THRESHOLD': os.environ.get('CPU_GREEN_THRESHOLD'),
        'CPU_YELLOW_THRESHOLD': os.environ.get('CPU_YELLOW_THRESHOLD'),
        'CPU_RED_THRESHOLD': os.environ.get('CPU_RED_THRESHOLD')
    }
    
    try:
        # Set test values
        os.environ['CPU_GREEN_THRESHOLD'] = '70'
        os.environ['CPU_YELLOW_THRESHOLD'] = '80'
        os.environ['CPU_RED_THRESHOLD'] = '90'
        
        from app.monitoring.cpu_monitor import initialize_cpu_monitor
        
        # Simulate main.py initialization logic
        monitor = initialize_cpu_monitor(
            green_threshold=float(os.getenv('CPU_GREEN_THRESHOLD', '75')),
            yellow_threshold=float(os.getenv('CPU_YELLOW_THRESHOLD', '85')),
            red_threshold=float(os.getenv('CPU_RED_THRESHOLD', '95'))
        )
        
        assert monitor.green_threshold == 70.0
        assert monitor.yellow_threshold == 80.0  
        assert monitor.red_threshold == 90.0
        
        monitor.stop_monitoring()
        print("✅ Test 3 PASSED: Environment overrides work correctly")
        return True
        
    finally:
        # Restore original env
        for key, value in backup_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]

def test_4_statistics_reporting():
    """Test 4: Statistics include new thresholds"""
    print("\n🧪 Test 4: Statistics Reporting")
    
    from app.monitoring.cpu_monitor import CPUSafetyMonitor
    
    monitor = CPUSafetyMonitor()
    stats = monitor.get_statistics()
    
    # Verify threshold reporting
    assert stats['thresholds']['green_threshold'] == 75.0
    assert stats['thresholds']['yellow_threshold'] == 85.0
    assert stats['thresholds']['red_threshold'] == 95.0
    
    monitor.stop_monitoring()
    print("✅ Test 4 PASSED: Statistics report correct thresholds")
    return True

def test_5_docker_config():
    """Test 5: Docker configuration has new defaults"""
    print("\n🧪 Test 5: Docker Configuration")
    
    # Read docker-compose file
    with open('docker-compose.prod-minimal.yml', 'r') as f:
        content = f.read()
    
    # Verify new defaults are in the file
    assert 'CPU_GREEN_THRESHOLD:-75' in content, "Docker config should have green threshold 75"
    assert 'CPU_YELLOW_THRESHOLD:-85' in content, "Docker config should have yellow threshold 85"
    assert 'CPU_RED_THRESHOLD:-95' in content, "Docker config should have red threshold 95"
    
    print("✅ Test 5 PASSED: Docker configuration updated")
    return True

def test_6_code_documentation():
    """Test 6: Code documentation reflects new thresholds"""
    print("\n🧪 Test 6: Documentation Updates")
    
    # Check CPU monitor file
    with open('app/monitoring/cpu_monitor.py', 'r') as f:
        content = f.read()
    
    # Verify documentation was updated
    assert 'Green Zone (0-75%)' in content, "Documentation should show Green Zone (0-75%)"
    assert 'Yellow Zone (75-85%)' in content, "Documentation should show Yellow Zone (75-85%)"
    assert 'Red Zone (85-95%)' in content, "Documentation should show Red Zone (85-95%)"
    assert 'Critical Zone (95%+)' in content, "Documentation should show Critical Zone (95%+)"
    
    print("✅ Test 6 PASSED: Documentation updated correctly")
    return True

def main():
    """Run all pre-commit tests"""
    print("🚀 Final Pre-Commit Test Suite")
    print("==============================")
    
    tests = [
        test_1_cpu_monitor_defaults,
        test_2_zone_determination,
        test_3_environment_overrides,
        test_4_statistics_reporting,
        test_5_docker_config,
        test_6_code_documentation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} PASSED, {failed} FAILED")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ CPU threshold configuration successfully updated")
        print("✅ All code, documentation, and configuration files updated")
        print("✅ Environment variable overrides working")
        print("✅ Docker configuration updated")
        print("\n🚀 READY FOR REPOSITORY COMMIT!")
        return True
    else:
        print(f"\n❌ {failed} TESTS FAILED - NOT READY FOR COMMIT")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)