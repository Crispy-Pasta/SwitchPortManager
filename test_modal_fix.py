#!/usr/bin/env python3
"""
Test script to verify the delete site functionality and modal fixes
in the DellPortTracer application.
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
TEST_SITE_NAME = f"TEST_MODAL_SITE_{int(time.time())}"

class PortTracerAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.site_id = None
        
    def login(self, username="admin", password="admin"):
        """Login to the application"""
        print("🔐 Logging in...")
        login_data = {
            'username': username,
            'password': password
        }
        
        response = self.session.post(f"{BASE_URL}/login", data=login_data)
        if response.status_code == 200:
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False
    
    def create_test_site(self):
        """Create a test site"""
        print(f"🏗️  Creating test site: {TEST_SITE_NAME}")
        site_data = {
            'name': TEST_SITE_NAME,
            'description': 'Test site for modal functionality verification'
        }
        
        response = self.session.post(f"{BASE_URL}/api/sites", json=site_data)
        if response.status_code == 201:
            result = response.json()
            self.site_id = result.get('site', {}).get('id')
            print(f"✅ Site created successfully with ID: {self.site_id}")
            return True
        else:
            print(f"❌ Site creation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    def get_sites(self):
        """Retrieve all sites"""
        print("📋 Retrieving sites list...")
        response = self.session.get(f"{BASE_URL}/api/sites")
        if response.status_code == 200:
            sites = response.json()
            print(f"✅ Retrieved {len(sites)} sites")
            
            # Find our test site
            test_site = next((site for site in sites if site['name'] == TEST_SITE_NAME), None)
            if test_site:
                print(f"✅ Test site found: {test_site['name']} (ID: {test_site['id']})")
                return True
            else:
                print("❌ Test site not found in sites list")
                return False
        else:
            print(f"❌ Failed to retrieve sites: {response.status_code}")
            return False
    
    def delete_site(self):
        """Delete the test site"""
        if not self.site_id:
            print("❌ No site ID available for deletion")
            return False
            
        print(f"🗑️  Deleting site ID: {self.site_id}")
        response = self.session.delete(f"{BASE_URL}/api/sites/{self.site_id}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Site deleted successfully: {result.get('message', 'Success')}")
            return True
        else:
            print(f"❌ Site deletion failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    def verify_deletion(self):
        """Verify the site was actually deleted"""
        print("🔍 Verifying site deletion...")
        response = self.session.get(f"{BASE_URL}/api/sites")
        if response.status_code == 200:
            sites = response.json()
            test_site = next((site for site in sites if site['name'] == TEST_SITE_NAME), None)
            if not test_site:
                print("✅ Site successfully deleted - not found in sites list")
                return True
            else:
                print("❌ Site still exists after deletion")
                return False
        else:
            print(f"❌ Failed to verify deletion: {response.status_code}")
            return False
    
    def test_modal_javascript_fix(self):
        """Check if the modal fix is present in the HTML"""
        print("🔧 Checking modal JavaScript fix...")
        response = self.session.get(f"{BASE_URL}/inventory")
        if response.status_code == 200:
            html_content = response.text
            
            # Check for the fixed closeModal function
            if "querySelectorAll('.modal-overlay')" in html_content and "forEach(modal =>" in html_content:
                print("✅ Modal fix is present in the HTML")
                return True
            else:
                print("❌ Modal fix not found in HTML")
                return False
        else:
            print(f"❌ Failed to retrieve inventory page: {response.status_code}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting DellPortTracer Modal Fix Tests")
        print("=" * 50)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test Site: {TEST_SITE_NAME}")
        print("=" * 50)
        
        tests = [
            ("Login Test", self.login),
            ("Modal JavaScript Fix Check", self.test_modal_javascript_fix),
            ("Create Test Site", self.create_test_site),
            ("Retrieve Sites", self.get_sites),
            ("Delete Site", self.delete_site),
            ("Verify Deletion", self.verify_deletion)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running: {test_name}")
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} FAILED with exception: {str(e)}")
        
        print("\n" + "=" * 50)
        print("🏁 TEST RESULTS SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Modal fix is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the output above.")
            return False

def main():
    """Main function"""
    tester = PortTracerAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()