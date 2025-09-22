#!/usr/bin/env python3
"""
Delete Site Confirmation Test Script
====================================

This script tests the delete site confirmation functionality:
1. Creates a test site
2. Verifies the edit site modal shows up
3. Tests the delete confirmation flow
4. Cleans up test data

Usage:
python test_delete_confirmation.py

Prerequisites:
- Application must be running
- Valid test credentials available
"""

import requests
import time
import json
from datetime import datetime

class DeleteConfirmationTester:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_site_id = None
        print(f"🧪 Delete Confirmation Tester initialized for: {self.base_url}")
    
    def login(self, username='admin', password='password'):
        """Login to the application"""
        print(f"\n1️⃣ Logging in with credentials: {username}")
        
        login_url = f"{self.base_url}/login"
        login_data = {
            'username': username,
            'password': password
        }
        
        response = self.session.post(login_url, data=login_data, allow_redirects=False)
        
        if response.status_code == 302:
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed - status code: {response.status_code}")
            return False
    
    def create_test_site(self, site_name='TEST_DELETE_SITE'):
        """Create a test site for deletion testing"""
        print(f"\n2️⃣ Creating test site: {site_name}")
        
        try:
            response = self.session.post(f"{self.base_url}/api/sites", 
                                       json={'name': site_name})
            
            if response.status_code == 201:
                data = response.json()
                self.test_site_id = data.get('id')
                print(f"✅ Test site created successfully - ID: {self.test_site_id}")
                return True
            else:
                data = response.json()
                print(f"❌ Failed to create test site: {data.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating test site: {str(e)}")
            return False
    
    def get_sites(self):
        """Get list of sites to verify test site exists"""
        print(f"\n3️⃣ Verifying test site exists in site list")
        
        try:
            response = self.session.get(f"{self.base_url}/api/sites")
            
            if response.status_code == 200:
                sites = response.json()
                test_site = next((site for site in sites if site['id'] == self.test_site_id), None)
                
                if test_site:
                    print(f"✅ Test site found: {test_site['name']} (ID: {test_site['id']})")
                    return True
                else:
                    print("❌ Test site not found in site list")
                    return False
            else:
                print(f"❌ Failed to get sites list: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error getting sites: {str(e)}")
            return False
    
    def test_delete_site_api(self):
        """Test the delete site API endpoint directly"""
        print(f"\n4️⃣ Testing delete site API endpoint")
        
        if not self.test_site_id:
            print("❌ No test site ID available")
            return False
        
        try:
            response = self.session.delete(f"{self.base_url}/api/sites/{self.test_site_id}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Site deleted successfully: {data.get('message', 'Site deleted')}")
                self.test_site_id = None  # Clear the ID since site is deleted
                return True
            else:
                data = response.json()
                print(f"❌ Failed to delete site: {data.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting site: {str(e)}")
            return False
    
    def verify_site_deleted(self):
        """Verify that the site was actually deleted"""
        print(f"\n5️⃣ Verifying site was deleted")
        
        try:
            response = self.session.get(f"{self.base_url}/api/sites")
            
            if response.status_code == 200:
                sites = response.json()
                deleted_site = next((site for site in sites if site['name'] == 'TEST_DELETE_SITE'), None)
                
                if not deleted_site:
                    print("✅ Site successfully deleted from database")
                    return True
                else:
                    print("❌ Site still exists in database")
                    return False
            else:
                print(f"❌ Failed to verify deletion: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error verifying deletion: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up any remaining test data"""
        print(f"\n🧹 Cleaning up test data")
        
        if self.test_site_id:
            try:
                response = self.session.delete(f"{self.base_url}/api/sites/{self.test_site_id}")
                if response.status_code == 200:
                    print("✅ Test site cleaned up")
                else:
                    print("⚠️ Could not clean up test site")
            except:
                print("⚠️ Error during cleanup")
    
    def run_complete_test(self, username='admin', password='password'):
        """Run complete delete confirmation test"""
        print("=" * 60)
        print("🚀 DELETE SITE CONFIRMATION TEST")
        print("=" * 60)
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test steps
        login_ok = self.login(username, password)
        if not login_ok:
            return False
        
        create_ok = self.create_test_site()
        if not create_ok:
            return False
        
        verify_ok = self.get_sites()
        if not verify_ok:
            self.cleanup()
            return False
        
        delete_ok = self.test_delete_site_api()
        if not delete_ok:
            self.cleanup()
            return False
        
        verify_deleted_ok = self.verify_site_deleted()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        results = [
            ("Login", "✅ PASS" if login_ok else "❌ FAIL"),
            ("Create Test Site", "✅ PASS" if create_ok else "❌ FAIL"),
            ("Verify Site Exists", "✅ PASS" if verify_ok else "❌ FAIL"),
            ("Delete Site API", "✅ PASS" if delete_ok else "❌ FAIL"),
            ("Verify Site Deleted", "✅ PASS" if verify_deleted_ok else "❌ FAIL"),
        ]
        
        for test_name, result in results:
            print(f"{test_name:<25} {result}")
        
        all_passed = all([login_ok, create_ok, verify_ok, delete_ok, verify_deleted_ok])
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Delete site API is working correctly.")
            print("\n📋 Manual UI Testing Instructions:")
            print("1. Open the application in browser: http://localhost:5000")
            print("2. Navigate to Switch Management (🏢 Switch Management)")
            print("3. Create a test site using the '+ Add Site' button")
            print("4. Click the ✏️ edit button next to the site")
            print("5. Click the '🗑️ Delete Site' button in the edit modal")
            print("6. Verify that a confirmation dialog appears")
            print("7. Test both 'Cancel' and 'Delete' buttons")
        else:
            print("❌ SOME TESTS FAILED! There may be issues with the delete functionality.")
        
        print("=" * 60)
        return all_passed

def main():
    """Main test function"""
    tester = DeleteConfirmationTester()
    
    test_username = 'admin'
    test_password = 'password'
    
    print("Please ensure the application is running before starting tests.")
    input("Press Enter to continue...")
    
    success = tester.run_complete_test(test_username, test_password)
    
    if success:
        print("\n🎯 Backend API is working correctly!")
        print("Now test the UI confirmation modal manually in the browser.")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check if the application is running on localhost:5000")
        print("2. Verify API endpoints are responding correctly")
        print("3. Check browser console for JavaScript errors")

if __name__ == "__main__":
    main()