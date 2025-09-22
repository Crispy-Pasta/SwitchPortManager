#!/usr/bin/env python3
"""
Simple test to verify modal fix and basic functionality
"""

import requests
import re

BASE_URL = "http://localhost:5000"

def test_modal_fix():
    """Test that the modal fix is present"""
    print("🔧 Testing modal fix...")
    
    try:
        # Get the inventory page
        response = requests.get(f"{BASE_URL}/inventory")
        if response.status_code == 200:
            html_content = response.text
            
            # Look for the specific pattern in our fix
            if "querySelectorAll('.modal-overlay')" in html_content and "modals.forEach(modal =>" in html_content:
                print("✅ Modal fix FOUND in HTML!")
                return True
            else:
                print("❌ Modal fix NOT found in HTML")
                
                # Let's search for just the function
                if "function closeModal()" in html_content:
                    print("📋 closeModal function found, checking content...")
                    
                    # Extract the closeModal function
                    match = re.search(r'function closeModal\(\)\s*{([^}]+)}', html_content)
                    if match:
                        function_body = match.group(1)
                        print(f"Function body: {function_body.strip()}")
                        
                        if "querySelectorAll" in function_body:
                            print("✅ Fixed function found!")
                            return True
                    
                return False
        else:
            print(f"❌ Failed to get inventory page: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing modal fix: {str(e)}")
        return False

def test_basic_connectivity():
    """Test basic connectivity"""
    print("🌐 Testing basic connectivity...")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Basic connectivity OK")
            return True
        else:
            print(f"❌ Basic connectivity failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connectivity error: {str(e)}")
        return False

def main():
    print("🚀 Simple DellPortTracer Modal Fix Test")
    print("=" * 40)
    
    results = []
    results.append(("Basic Connectivity", test_basic_connectivity()))
    results.append(("Modal Fix Check", test_modal_fix()))
    
    print("\n" + "=" * 40)
    print("📊 Results:")
    
    passed = 0
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        emoji = "✅" if result else "❌"
        print(f"{emoji} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The modal fix is in place.")
    else:
        print("⚠️  Some tests failed.")

if __name__ == "__main__":
    main()