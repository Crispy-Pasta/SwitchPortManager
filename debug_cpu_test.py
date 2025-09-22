#!/usr/bin/env python3
"""
Debug CPU Monitor Initialization
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.monitoring.cpu_monitor import CPUSafetyMonitor, initialize_cpu_monitor
    
    print("🔍 Debug: Testing CPU Monitor Creation...")
    
    # Test direct creation
    monitor1 = CPUSafetyMonitor()
    print(f"Direct creation - Green: {monitor1.green_threshold}, Yellow: {monitor1.yellow_threshold}, Red: {monitor1.red_threshold}")
    
    # Test initialize function
    monitor2 = initialize_cpu_monitor(
        green_threshold=75.0,
        yellow_threshold=85.0,
        red_threshold=95.0
    )
    print(f"Initialize function - Green: {monitor2.green_threshold}, Yellow: {monitor2.yellow_threshold}, Red: {monitor2.red_threshold}")
    
    # Clean up
    monitor1.stop_monitoring()
    if monitor2 != monitor1:  # Only stop if it's a different instance
        monitor2.stop_monitoring()
    
    print("✅ Both methods work correctly")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()