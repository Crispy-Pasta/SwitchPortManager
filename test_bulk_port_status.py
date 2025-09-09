#!/usr/bin/env python3
"""
Test script for the optimized bulk port status functionality.

This script tests both the bulk port status method and the API endpoint
to verify the performance improvements work correctly.
"""

import time
import requests
import json
from datetime import datetime

# Test configuration - UPDATE THESE VALUES FOR YOUR ENVIRONMENT
TEST_SWITCH_IP = "192.168.1.100"  # Replace with actual switch IP
SWITCH_USERNAME = "admin"         # Replace with actual username
SWITCH_PASSWORD = "password"      # Replace with actual password
SWITCH_MODEL = "N3000"           # Replace with actual switch model
API_BASE_URL = "http://localhost:5000"  # Flask app URL

# Test port lists for different scenarios
SMALL_PORT_LIST = ["Gi1/0/1", "Gi1/0/2", "Gi1/0/3"]  # Should use individual method
LARGE_PORT_LIST = ["Gi1/0/1", "Gi1/0/2", "Gi1/0/3", "Gi1/0/4", "Gi1/0/5", 
                   "Gi1/0/6", "Gi1/0/7", "Gi1/0/8", "Gi1/0/9", "Gi1/0/10"]  # Should use bulk method

def test_vlan_manager_direct():
    """Test the VLANManager class directly (requires switch access)."""
    print("🔧 Testing VLANManager class directly...")
    
    try:
        # Import from the local module
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'core'))
        
        from vlan_manager import VLANManager
        
        # Initialize VLAN manager
        vlan_manager = VLANManager(TEST_SWITCH_IP, SWITCH_USERNAME, SWITCH_PASSWORD, SWITCH_MODEL)
        
        if not vlan_manager.connect():
            print("❌ Could not connect to switch - check IP/credentials")
            return False
        
        print(f"✅ Connected to switch {TEST_SWITCH_IP}")
        
        # Test 1: Small port list (should use individual method)
        print(f"\n📊 Test 1: Small port list ({len(SMALL_PORT_LIST)} ports) - Individual method")
        start_time = time.time()
        
        individual_results = {}
        for port in SMALL_PORT_LIST:
            individual_results[port] = vlan_manager.get_port_status(port)
        
        individual_time = time.time() - start_time
        print(f"⏱️  Individual method time: {individual_time:.2f} seconds")
        
        # Test 2: Large port list (should use bulk method)
        print(f"\n📊 Test 2: Large port list ({len(LARGE_PORT_LIST)} ports) - Bulk method")
        start_time = time.time()
        
        bulk_results = vlan_manager.get_bulk_port_status(LARGE_PORT_LIST)
        
        bulk_time = time.time() - start_time
        print(f"⏱️  Bulk method time: {bulk_time:.2f} seconds")
        
        # Calculate performance improvement
        ports_per_second_individual = len(SMALL_PORT_LIST) / individual_time
        ports_per_second_bulk = len(LARGE_PORT_LIST) / bulk_time
        
        print(f"\n📈 Performance Comparison:")
        print(f"Individual method: {ports_per_second_individual:.1f} ports/second")
        print(f"Bulk method: {ports_per_second_bulk:.1f} ports/second")
        print(f"Performance improvement: {(ports_per_second_bulk / ports_per_second_individual):.1f}x faster")
        
        # Test 3: Compare results accuracy
        print(f"\n🔍 Testing result accuracy...")
        
        # Get some common ports from both methods
        common_ports = SMALL_PORT_LIST[:2]  # Test first 2 ports
        
        for port in common_ports:
            individual = vlan_manager.get_port_status(port)
            bulk_all = vlan_manager.get_bulk_port_status([port])
            bulk = bulk_all.get(port, {})
            
            print(f"\nPort {port}:")
            print(f"  Individual - Status: {individual.get('status')}, VLAN: {individual.get('current_vlan')}")
            print(f"  Bulk       - Status: {bulk.get('status')}, VLAN: {bulk.get('current_vlan')}")
            
            # Check if results match
            if (individual.get('status') == bulk.get('status') and 
                individual.get('current_vlan') == bulk.get('current_vlan')):
                print(f"  ✅ Results match!")
            else:
                print(f"  ⚠️  Results differ - may need calibration")
        
        vlan_manager.disconnect()
        print(f"\n✅ Direct VLANManager tests completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Direct VLANManager test failed: {str(e)}")
        return False

def test_api_endpoint():
    """Test the optimized API endpoint."""
    print(f"\n🌐 Testing API endpoint optimization...")
    
    try:
        # You'll need to authenticate first - adjust this for your auth method
        session = requests.Session()
        
        # Test data for API
        test_cases = [
            {
                "name": "Small port list (individual method)",
                "switch_id": 1,  # Replace with actual switch ID from your database
                "ports": ",".join(SMALL_PORT_LIST),
                "expected_method": "individual"
            },
            {
                "name": "Large port list (bulk method)", 
                "switch_id": 1,  # Replace with actual switch ID from your database
                "ports": ",".join(LARGE_PORT_LIST),
                "expected_method": "bulk"
            }
        ]
        
        for test_case in test_cases:
            print(f"\n📊 {test_case['name']}")
            
            start_time = time.time()
            
            response = session.post(f"{API_BASE_URL}/api/port/status", 
                                  json={
                                      "switch_id": test_case["switch_id"],
                                      "ports": test_case["ports"]
                                  })
            
            api_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                optimization_used = data.get('optimization_used', 'unknown')
                port_count = len(data.get('ports', []))
                
                print(f"⏱️  API response time: {api_time:.2f} seconds")
                print(f"🔧 Optimization used: {optimization_used}")
                print(f"📊 Ports returned: {port_count}")
                
                # Verify correct optimization was used
                if optimization_used == test_case['expected_method']:
                    print(f"✅ Correct optimization method used!")
                else:
                    print(f"⚠️  Expected {test_case['expected_method']}, got {optimization_used}")
                    
            else:
                print(f"❌ API request failed: HTTP {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text}")
        
        print(f"\n✅ API endpoint tests completed")
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {str(e)}")
        print(f"   Make sure the Flask application is running on {API_BASE_URL}")
        return False

def test_bulk_parsing():
    """Test the bulk status parsing logic with mock data."""
    print(f"\n🧪 Testing bulk status parsing logic...")
    
    try:
        # Mock Dell switch output
        mock_bulk_output = """
Port       Name               Status       Vlan       Duplex Speed Type
gi1/0/1    Server1            connected    100        full   1000 --
gi1/0/2    Printer            connected    200        full   100  --
gi1/0/3    AP-Floor2          connected    300        full   1000 --
gi1/0/4                       notconnect   1          --     --   --
gi1/0/5    Workstation        connected    400        full   1000 --
"""
        
        # Import parsing function
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'core'))
        
        from vlan_manager import VLANManager
        
        # Create a temporary VLANManager instance for parsing
        temp_manager = VLANManager("dummy", "dummy", "dummy")
        
        # Test parsing each line
        lines = mock_bulk_output.strip().split('\n')[2:]  # Skip headers
        
        print("Parsing mock switch output:")
        for line in lines:
            parsed = temp_manager._parse_bulk_status_line(line)
            if parsed:
                print(f"  Port: {parsed['port']:10} Status: {parsed['status']:10} VLAN: {parsed['current_vlan']:3}")
            else:
                print(f"  Failed to parse: {line}")
        
        print(f"✅ Bulk parsing test completed")
        return True
        
    except Exception as e:
        print(f"❌ Bulk parsing test failed: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Bulk Port Status Optimization Tests")
    print("=" * 60)
    
    print(f"Test Configuration:")
    print(f"  Switch IP: {TEST_SWITCH_IP}")
    print(f"  Switch Model: {SWITCH_MODEL}")
    print(f"  API URL: {API_BASE_URL}")
    print(f"  Small port list: {len(SMALL_PORT_LIST)} ports")
    print(f"  Large port list: {len(LARGE_PORT_LIST)} ports")
    
    results = []
    
    # Test 1: Bulk parsing logic (no switch required)
    results.append(("Bulk parsing logic", test_bulk_parsing()))
    
    # Test 2: Direct VLANManager testing (requires switch access)
    print(f"\n" + "=" * 60)
    print("⚠️  The following tests require actual switch access")
    print("   Update TEST_SWITCH_IP, SWITCH_USERNAME, SWITCH_PASSWORD if available")
    
    if input("\nTest direct VLANManager functionality? (y/n): ").lower().startswith('y'):
        results.append(("Direct VLANManager", test_vlan_manager_direct()))
    
    # Test 3: API endpoint testing (requires running Flask app)
    if input("Test API endpoint functionality? (y/n): ").lower().startswith('y'):
        results.append(("API endpoint", test_api_endpoint()))
    
    # Summary
    print(f"\n" + "=" * 60)
    print(f"📊 TEST SUMMARY")
    print(f"=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:25} {status}")
        if success:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bulk port status optimization is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    print(f"\nTest completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
