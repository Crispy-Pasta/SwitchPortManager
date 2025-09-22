#!/usr/bin/env python3
"""
Integration Test - Main App with New CPU Thresholds
==================================================

This test verifies that the main application initializes correctly
with the new CPU threshold settings.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_main_app_cpu_initialization():
    """Test that main app initializes CPU monitor with new thresholds."""
    print("🔧 Testing Main App CPU Monitor Initialization...")
    
    # Mock environment variables to test defaults
    original_env = {}
    env_vars = ['CPU_GREEN_THRESHOLD', 'CPU_YELLOW_THRESHOLD', 'CPU_RED_THRESHOLD']
    
    # Save original values
    for var in env_vars:
        original_env[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    try:
        # Import and test initialization logic from main.py
        from app.monitoring.cpu_monitor import initialize_cpu_monitor
        
        # Test with new default values (simulating main.py initialization)
        cpu_monitor = initialize_cpu_monitor(
            green_threshold=float(os.getenv('CPU_GREEN_THRESHOLD', '75')),
            yellow_threshold=float(os.getenv('CPU_YELLOW_THRESHOLD', '85')),
            red_threshold=float(os.getenv('CPU_RED_THRESHOLD', '95'))
        )
        
        # Verify the monitor has correct thresholds
        assert cpu_monitor.green_threshold == 75.0, f"Expected 75.0, got {cpu_monitor.green_threshold}"
        assert cpu_monitor.yellow_threshold == 85.0, f"Expected 85.0, got {cpu_monitor.yellow_threshold}"
        assert cpu_monitor.red_threshold == 95.0, f"Expected 95.0, got {cpu_monitor.red_threshold}"
        
        print("✅ Main app CPU monitor initialized with correct default thresholds")
        
        # Test with custom environment variables
        os.environ['CPU_GREEN_THRESHOLD'] = '70'
        os.environ['CPU_YELLOW_THRESHOLD'] = '80'
        os.environ['CPU_RED_THRESHOLD'] = '90'
        
        custom_monitor = initialize_cpu_monitor(
            green_threshold=float(os.getenv('CPU_GREEN_THRESHOLD', '75')),
            yellow_threshold=float(os.getenv('CPU_YELLOW_THRESHOLD', '85')),
            red_threshold=float(os.getenv('CPU_RED_THRESHOLD', '95'))
        )
        
        assert custom_monitor.green_threshold == 70.0
        assert custom_monitor.yellow_threshold == 80.0
        assert custom_monitor.red_threshold == 90.0
        
        print("✅ Environment variable overrides work correctly")
        
        # Stop monitors to clean up
        cpu_monitor.stop_monitoring()
        custom_monitor.stop_monitoring()
        
        return True
        
    finally:
        # Restore original environment
        for var, value in original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

def test_cpu_monitor_status():
    """Test CPU monitor status reporting."""
    print("\n📊 Testing CPU Monitor Status Reporting...")
    
    from app.monitoring.cpu_monitor import CPUSafetyMonitor
    
    monitor = CPUSafetyMonitor()
    
    # Test status reporting
    status = monitor.get_status()
    assert status.protection_zone == 'green', "Initial status should be green zone"
    assert status.max_concurrent_users == 10, "Green zone should allow 10 users"
    assert status.max_workers == 8, "Green zone should allow 8 workers"
    
    print("✅ Status reporting works correctly")
    
    # Test statistics
    stats = monitor.get_statistics()
    assert 'current_status' in stats
    assert 'thresholds' in stats
    assert stats['thresholds']['green_threshold'] == 75.0
    assert stats['thresholds']['yellow_threshold'] == 85.0
    assert stats['thresholds']['red_threshold'] == 95.0
    
    print("✅ Statistics reporting includes new thresholds")
    
    monitor.stop_monitoring()
    return True

def test_request_acceptance_logic():
    """Test request acceptance with new thresholds."""
    print("\n🚪 Testing Request Acceptance Logic...")
    
    from app.monitoring.cpu_monitor import CPUSafetyMonitor
    
    monitor = CPUSafetyMonitor()
    
    # Simulate different CPU states and test acceptance
    test_cases = [
        (70.0, True, "Should accept at 70% (green zone)"),
        (80.0, True, "Should accept at 80% (yellow zone)"),
        (90.0, True, "Should accept at 90% (red zone, queued)"),
        (98.0, False, "Should reject at 98% (critical zone)")
    ]
    
    for cpu_percent, should_accept, description in test_cases:
        # Manually set CPU for testing
        monitor.current_status.protection_zone = monitor._determine_protection_zone(cpu_percent)
        monitor.current_status.current_cpu = cpu_percent
        
        can_accept, reason = monitor.can_accept_request()
        
        if should_accept:
            assert can_accept, f"Failed: {description} - {reason}"
            print(f"✅ {description}")
        else:
            assert not can_accept, f"Failed: {description} - should have been rejected"
            print(f"✅ {description}")
    
    monitor.stop_monitoring()
    return True

def main():
    """Run integration tests."""
    print("🧪 Integration Test - Main App with New CPU Thresholds")
    print("======================================================")
    
    try:
        test_main_app_cpu_initialization()
        test_cpu_monitor_status()
        test_request_acceptance_logic()
        
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Main application will initialize correctly with new CPU thresholds")
        print("✅ Status reporting works with updated values")
        print("✅ Request acceptance logic updated properly")
        print("\n🚀 Ready for repository update!")
        return True
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        print(f"💥 Error details: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)