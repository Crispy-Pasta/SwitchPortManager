#!/usr/bin/env python3
"""
Debug Windows Authentication - Step by Step
"""

import os
import ldap3
import sys

def debug_windows_auth(username, password):
    """Debug Windows authentication step by step"""
    print(f"🔍 Debugging Windows Authentication for: {username}")
    print("=" * 60)
    
    # Step 1: Check configuration
    print("📋 Step 1: Configuration Check")
    ad_config = {
        'server': os.getenv('AD_SERVER', 'ldap://10.20.100.15'),
        'domain': os.getenv('AD_DOMAIN', 'kmc.int'),
        'base_dn': os.getenv('AD_BASE_DN', 'DC=kmc,DC=int'),
        'user_search_base': os.getenv('AD_USER_SEARCH_BASE', 'DC=kmc,DC=int'),
        'group_search_base': os.getenv('AD_GROUP_SEARCH_BASE', 'DC=kmc,DC=int')
    }
    
    for key, value in ad_config.items():
        print(f"   {key}: {value}")
    
    # Step 2: Test different username formats
    print(f"\n🔄 Step 2: Testing Username Formats for '{username}'")
    
    if '@' not in username:
        user_dn = f"{username}@{ad_config['domain']}"
    else:
        user_dn = username
    
    user_formats = [
        user_dn,  # user@domain.com format
        f"{ad_config['domain']}\\\\{username.split('@')[0] if '@' in username else username}",  # DOMAIN\username format
        f"CN={username.split('@')[0] if '@' in username else username},{ad_config['user_search_base']}"  # Distinguished Name format
    ]
    
    print("   Trying these formats:")
    for i, fmt in enumerate(user_formats, 1):
        print(f"   {i}. {fmt}")
    
    # Step 3: Test LDAP connection
    print(f"\n🌐 Step 3: LDAP Connection Test")
    try:
        server = ldap3.Server(ad_config['server'], get_info=ldap3.ALL)
        print(f"   Server created: {ad_config['server']}")
        
        # Try each username format
        for i, user_format in enumerate(user_formats, 1):
            print(f"\n   🧪 Testing format {i}: {user_format}")
            try:
                conn = ldap3.Connection(
                    server, 
                    user=user_format, 
                    password=password, 
                    auto_bind=False,
                    authentication=ldap3.SIMPLE
                )
                
                if conn.bind():
                    print(f"   ✅ Authentication SUCCESSFUL with format {i}")
                    
                    # Get user info
                    print(f"\n📊 Step 4: User Information Retrieval")
                    search_username = username.split('@')[0] if '@' in username else username
                    search_filter = f"(sAMAccountName={search_username})"
                    
                    print(f"   Search base: {ad_config['user_search_base']}")
                    print(f"   Search filter: {search_filter}")
                    
                    conn.search(
                        ad_config['user_search_base'], 
                        search_filter,
                        attributes=['cn', 'mail', 'sAMAccountName', 'displayName', 'memberOf']
                    )
                    
                    if conn.entries:
                        entry = conn.entries[0]
                        print(f"   ✅ User found in AD:")
                        print(f"      Username: {entry.sAMAccountName}")
                        print(f"      Display Name: {entry.displayName}")
                        print(f"      Email: {entry.mail}")
                        print(f"      Groups: {len(entry.memberOf) if entry.memberOf else 0} groups")
                        
                        if entry.memberOf:
                            print(f"      Group memberships:")
                            for group in entry.memberOf[:5]:  # Show first 5 groups
                                print(f"        - {group}")
                            if len(entry.memberOf) > 5:
                                print(f"        ... and {len(entry.memberOf) - 5} more groups")
                    else:
                        print(f"   ❌ User not found in AD search")
                    
                    conn.unbind()
                    return True
                else:
                    print(f"   ❌ Authentication failed with format {i}")
                    if conn.result:
                        print(f"      Error: {conn.result}")
                    
            except Exception as e:
                print(f"   ❌ Exception with format {i}: {str(e)}")
                continue
        
        print(f"\n❌ All authentication formats failed")
        return False
        
    except Exception as e:
        print(f"❌ LDAP connection error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Dell Port Tracer - Windows Authentication Debug Tool")
    print("=" * 60)
    
    if len(sys.argv) != 3:
        print("Usage: python3 debug-windows-auth.py <username> <password>")
        print("Example: python3 debug-windows-auth.py janestrada mypassword")
        print("Example: python3 debug-windows-auth.py janestrada@kmc.int mypassword")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    success = debug_windows_auth(username, password)
    
    if success:
        print(f"\n🎉 Windows authentication should work for {username}")
    else:
        print(f"\n❌ Windows authentication failed for {username}")
        print("\n🔧 Troubleshooting steps:")
        print("1. Verify username and password are correct")
        print("2. Check if account is locked or disabled")
        print("3. Verify LDAP server connectivity")
        print("4. Check domain configuration")
