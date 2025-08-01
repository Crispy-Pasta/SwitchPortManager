#!/usr/bin/env python3
import ldap3
import os

def test_ldap_connection():
    server_ip = "10.20.100.15"
    print(f"Testing LDAP connection to {server_ip}...")
    
    try:
        server = ldap3.Server(f"ldap://{server_ip}", get_info=ldap3.ALL, connect_timeout=5)
        conn = ldap3.Connection(server, auto_bind=False)
        
        if conn.bind():
            print("✅ LDAP Connection: SUCCESS")
            if server.info:
                print(f"   Server: {getattr(server.info, 'vendor_name', 'Unknown')}")
                print(f"   Base DN available: {getattr(server.info, 'naming_contexts', [])}")
            conn.unbind()
            return True
        else:
            print("❌ LDAP Connection: Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ LDAP Connection: {str(e)}")
        return False

if __name__ == "__main__":
    print("Dell Port Tracer - LDAP Connection Test")
    print("=" * 50)
    
    success = test_ldap_connection()
    
    if success:
        print("\n🎉 LDAP server is reachable!")
        print("Windows authentication should now work.")
    else:
        print("\n⚠️  LDAP connection failed.")
        print("Check network connectivity and server settings.")
