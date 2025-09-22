#!/usr/bin/env python3
"""
Session Timeout Test Script
===========================

This script tests the session timeout functionality to ensure:
1. Session keepalive API endpoint works correctly
2. Session check API endpoint returns proper status
3. Session timeout behavior is working as expected

Usage:
python test_session_timeout.py

Prerequisites:
- Application must be running
- Valid test credentials available
"""

import requests
import time
import json
from datetime import datetime

class SessionTimeoutTester:
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        print(f"🧪 Session Timeout Tester initialized for: {self.base_url}")
    
    def test_login(self, username='admin', password='password'):
        """Test login functionality"""
        print(f"\n1️⃣ Testing login with credentials: {username}")
        
        login_url = f"{self.base_url}/login"
        login_data = {
            'username': username,
            'password': password
        }
        
        response = self.session.post(login_url, data=login_data, allow_redirects=False)
        
        if response.status_code == 302:
            print("✅ Login successful - redirected")
            return True
        elif response.status_code == 200:
            if 'Invalid credentials' in response.text:
                print("❌ Login failed - invalid credentials")
                return False
            else:
                print("✅ Login successful - no redirect needed")
                return True
        else:
            print(f"❌ Login failed - status code: {response.status_code}")
            return False
    
    def test_session_check(self):
        """Test session check API endpoint"""
        print(f"\n2️⃣ Testing session check API endpoint")
        
        check_url = f"{self.base_url}/api/session/check"
        
        try:
            response = self.session.post(check_url)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Session check successful")
                print(f"   - Valid: {data.get('valid', 'N/A')}")
                print(f"   - Username: {data.get('username', 'N/A')}")
                print(f"   - Role: {data.get('role', 'N/A')}")
                print(f"   - Time remaining: {data.get('time_remaining_minutes', 'N/A')} minutes")
                return True
            elif response.status_code == 401:
                print("❌ Session check failed - not authenticated")
                return False
            else:
                print(f"❌ Session check failed - status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Session check error: {str(e)}")
            return False
    
    def test_session_keepalive(self):
        """Test session keepalive API endpoint"""
        print(f"\n3️⃣ Testing session keepalive API endpoint")
        
        keepalive_url = f"{self.base_url}/api/session/keepalive"
        
        try:
            response = self.session.post(keepalive_url, json={})
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ Session keepalive successful")
                    print(f"   - Message: {data.get('message', 'N/A')}")
                    print(f"   - Timeout minutes: {data.get('timeout_minutes', 'N/A')}")
                    return True
                else:
                    print(f"❌ Session keepalive failed: {data.get('error', 'Unknown error')}")
                    return False
            elif response.status_code == 401:
                print("❌ Session keepalive failed - not authenticated")
                return False
            else:
                print(f"❌ Session keepalive failed - status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Session keepalive error: {str(e)}")
            return False
    
    def test_main_page_access(self):
        """Test access to main page"""
        print(f"\n4️⃣ Testing main page access")
        
        main_url = f"{self.base_url}/"
        
        try:
            response = self.session.get(main_url, allow_redirects=False)
            
            if response.status_code == 200:
                print("✅ Main page accessible - user is logged in")
                return True
            elif response.status_code == 302:
                location = response.headers.get('Location', '')
                if 'login' in location:
                    print("❌ Main page redirected to login - session expired")
                    return False
                else:
                    print(f"✅ Main page redirected to: {location}")
                    return True
            else:
                print(f"❌ Main page access failed - status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Main page access error: {str(e)}")
            return False
    
    def run_complete_test(self, username='admin', password='password'):
        """Run complete session timeout test"""
        print("=" * 60)
        print("🚀 DELL PORT TRACER - SESSION TIMEOUT TEST")
        print("=" * 60)
        print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 1: Login
        if not self.test_login(username, password):
            print("\n❌ TEST SUITE FAILED - Cannot proceed without login")
            return False
        
        # Test 2: Session Check
        session_check_ok = self.test_session_check()
        
        # Test 3: Session Keepalive
        keepalive_ok = self.test_session_keepalive()
        
        # Test 4: Main Page Access
        main_page_ok = self.test_main_page_access()
        
        # Test 5: Session Check Again (after keepalive)
        print(f"\n5️⃣ Testing session check after keepalive")
        session_check_after_ok = self.test_session_check()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        results = [
            ("Login", "✅ PASS" if True else "❌ FAIL"),
            ("Session Check", "✅ PASS" if session_check_ok else "❌ FAIL"),
            ("Session Keepalive", "✅ PASS" if keepalive_ok else "❌ FAIL"),
            ("Main Page Access", "✅ PASS" if main_page_ok else "❌ FAIL"),
            ("Session Check (After Keepalive)", "✅ PASS" if session_check_after_ok else "❌ FAIL"),
        ]
        
        for test_name, result in results:
            print(f"{test_name:<30} {result}")
        
        all_passed = all([session_check_ok, keepalive_ok, main_page_ok, session_check_after_ok])
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL TESTS PASSED! Session management is working correctly.")
            print("\n📋 Manual Testing Recommendations:")
            print("1. Open the application in a browser")
            print("2. Wait for 4 minutes (session warning should appear at 4 mins)")
            print("3. Test 'Stay Logged In' button functionality")
            print("4. Test 'Logout Now' button functionality")
            print("5. Test session timeout after 5 minutes of inactivity")
        else:
            print("❌ SOME TESTS FAILED! Please review the session management implementation.")
        
        print("=" * 60)
        return all_passed

def main():
    """Main test function"""
    tester = SessionTimeoutTester()
    
    # You can customize these credentials
    test_username = 'admin'
    test_password = 'password'
    
    print("Please ensure the application is running before starting tests.")
    input("Press Enter to continue...")
    
    success = tester.run_complete_test(test_username, test_password)
    
    if success:
        print("\n🔧 Next Steps:")
        print("1. Test the session timeout in a web browser")
        print("2. Verify the 'Stay Logged In' button works")
        print("3. Confirm automatic redirect to login page")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check if the application is running on localhost:5000")
        print("2. Verify the test credentials are correct")
        print("3. Review the application logs for errors")

if __name__ == "__main__":
    main()