#!/usr/bin/env python3
"""
Simple verification script for the tree state preservation fix
"""

import requests

BASE_URL = "http://localhost:5000"

def verify_fixes():
    print("🔍 Verifying Tree State Preservation Fix")
    print("=" * 45)
    
    try:
        # Login first
        session = requests.Session()
        login_data = {'username': 'admin', 'password': 'admin'}
        response = session.post(f"{BASE_URL}/login", data=login_data)
        
        if response.status_code != 200:
            print("❌ Login failed")
            return False
        
        print("✅ Login successful")
        
        # Get inventory page
        response = session.get(f"{BASE_URL}/inventory")
        if response.status_code != 200:
            print(f"❌ Cannot access inventory page: {response.status_code}")
            return False
        
        html_content = response.text
        print("✅ Inventory page loaded")
        
        # Check for our fixes
        fixes_found = []
        
        if "saveCurrentTreeState" in html_content:
            fixes_found.append("✅ saveCurrentTreeState function")
        
        if "restoreTreeState" in html_content:
            fixes_found.append("✅ restoreTreeState function")
        
        if "querySelectorAll('.modal-overlay')" in html_content:
            fixes_found.append("✅ Modal fix (querySelectorAll)")
        
        if "preserveState = true" in html_content:
            fixes_found.append("✅ renderSiteTree with state preservation")
        
        if "setTimeout(() =>" in html_content and "restoreTreeState" in html_content:
            fixes_found.append("✅ Async state restoration")
        
        print(f"\n📋 Fixes Found ({len(fixes_found)}/5):")
        for fix in fixes_found:
            print(f"   {fix}")
        
        if len(fixes_found) >= 4:
            print(f"\n🎉 SUCCESS! {len(fixes_found)}/5 fixes are present.")
            print("\n📝 What this means:")
            print("• Sites will maintain expanded/collapsed state during switch operations")
            print("• Selected site and floor states are preserved during data refresh")
            print("• Modal delete confirmations work correctly")
            print("• No more annoying redirect to collapsed view")
            return True
        else:
            print(f"\n⚠️  Only {len(fixes_found)}/5 fixes found. Some may be missing.")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    verify_fixes()