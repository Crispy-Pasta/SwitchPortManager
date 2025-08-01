#!/usr/bin/env python3
"""
Test Windows Authentication Configuration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_configuration():
    """Test Windows authentication configuration"""
    print("🔍 Testing Windows Authentication Configuration...")
    print("=" * 60)
    
    # Check if Windows auth is enabled
    use_windows_auth = os.getenv('USE_WINDOWS_AUTH', 'false').lower() == 'true'
    print(f"USE_WINDOWS_AUTH: {use_windows_auth}")
    
    if not use_windows_auth:
        print("❌ Windows authentication is DISABLED")
        print("   Set USE_WINDOWS_AUTH=true in .env file")
        return False
    
    print("✅ Windows authentication is ENABLED")
    
    # Check AD configuration
    ad_config = {
        'AD_SERVER': os.getenv('AD_SERVER'),
        'AD_DOMAIN': os.getenv('AD_DOMAIN'), 
        'AD_BASE_DN': os.getenv('AD_BASE_DN'),
        'AD_USER_SEARCH_BASE': os.getenv('AD_USER_SEARCH_BASE'),
        'AD_GROUP_SEARCH_BASE': os.getenv('AD_GROUP_SEARCH_BASE')
    }
    
    print("\n🔧 Active Directory Configuration:")
    all_configured = True
    for key, value in ad_config.items():
        if value:
            print(f"✅ {key}: {value}")
        else:
            print(f"❌ {key}: NOT SET")
            all_configured = False
    
    # Check optional settings
    print("\n🔒 Optional Settings:")
    optional_settings = {
        'AD_REQUIRED_GROUP': os.getenv('AD_REQUIRED_GROUP'),
        'AD_SERVICE_USER': os.getenv('AD_SERVICE_USER'),
        'AD_SERVICE_PASSWORD': '***' if os.getenv('AD_SERVICE_PASSWORD') else None
    }
    
    for key, value in optional_settings.items():
        if value:
            print(f"✅ {key}: {value}")
        else:
            print(f"⚪ {key}: Not configured (optional)")
    
    # Check ldap3 availability
    print("\n📦 Dependencies:")
    try:
        import ldap3
        print("✅ ldap3 library: Available")
    except ImportError:
        print("❌ ldap3 library: NOT AVAILABLE")
        print("   Run: pip install ldap3")
        all_configured = False
    
    print("\n" + "=" * 60)
    
    if all_configured:
        print("✅ Windows Authentication: READY")
        print("\n🧪 Test with these steps:")
        print("1. Try logging in with your domain credentials")
        print("2. Format: username (without @domain) or username@domain.com")
        print("3. Check logs for authentication details")
        return True
    else:
        print("❌ Windows Authentication: CONFIGURATION INCOMPLETE")
        print("   Please configure the missing settings above")
        return False

def test_connection():
    """Test LDAP connection to domain controller"""
    try:
        import ldap3
        
        ad_server = os.getenv('AD_SERVER')
        if not ad_server:
            print("❌ Cannot test connection: AD_SERVER not configured")
            return False
            
        print(f"\n🌐 Testing connection to: {ad_server}")
        
        # Test basic connection (without authentication)
        server = ldap3.Server(ad_server, get_info=ldap3.ALL, connect_timeout=10)
        conn = ldap3.Connection(server, auto_bind=False)
        
        if conn.bind():
            print("✅ LDAP Connection: SUCCESS")
            print(f"   Server Info: {server.info.vendor_name if server.info else 'Unknown'}")
            conn.unbind()
            return True
        else:
            print("❌ LDAP Connection: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Dell Port Tracer - Windows Authentication Test")
    print("=" * 60)
    
    config_ok = test_configuration()
    
    if config_ok:
        connection_ok = test_connection()
        
        if connection_ok:
            print("\n🎉 Windows Authentication setup appears to be working!")
        else:
            print("\n⚠️  Configuration looks correct, but connection test failed.")
            print("   This might be normal if running outside the domain network.")
    
    print("\n📝 Next steps:")
    print("1. Ensure .env file has correct AD settings")
    print("2. Restart the application: docker compose restart port-tracer")
    print("3. Test login with domain credentials")
    print("4. Check application logs for authentication details")
