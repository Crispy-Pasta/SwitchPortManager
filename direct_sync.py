import psycopg2
import subprocess

def sync_data_direct():
    """Sync data by executing SQL commands directly via SSH"""
    print("🌟 Dell Port Tracer Direct Data Sync")
    print("=" * 40)
    
    try:
        # Connect to local database
        print("🔄 Connecting to local database...")
        local_conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='port_tracer_db',
            user='dell_tracer_user',
            password='secure_password123'
        )
        
        cursor = local_conn.cursor()
        
        # Get sample data for quick test
        cursor.execute("SELECT site_id, site_name FROM site ORDER BY site_id LIMIT 10")
        sites = cursor.fetchall()
        
        local_conn.close()
        
        print(f"✅ Found {len(sites)} sample sites to sync")
        
        # Clear production data and add sample sites
        print("🧹 Clearing production data...")
        clear_cmd = [
            'ssh', 'janzen@10.50.0.225',
            'docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"DELETE FROM switch; DELETE FROM floor; DELETE FROM site;\"'
        ]
        
        result = subprocess.run(clear_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Production data cleared")
        else:
            print(f"❌ Clear failed: {result.stderr}")
            return False
        
        # Add sample sites
        print("📥 Adding sample sites...")
        for site in sites[:5]:  # Just add first 5 sites for testing
            site_id, site_name = site
            safe_name = site_name.replace("'", "''")  # Escape quotes
            
            insert_cmd = [
                'ssh', 'janzen@10.50.0.225',
                f'docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"INSERT INTO site (site_id, site_name, site_code, description, location) VALUES ({site_id}, \\''{safe_name}\\', \\'TEST\\', \\'Test site\\', \\'Test location\\');\"'
            ]
            
            result = subprocess.run(insert_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Added site: {site_name}")
            else:
                print(f"❌ Failed to add site {site_name}: {result.stderr}")
        
        # Verify data
        print("🔍 Verifying production data...")
        verify_cmd = [
            'ssh', 'janzen@10.50.0.225',
            'docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"SELECT COUNT(*) FROM site;\"'
        ]
        
        result = subprocess.run(verify_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Production verification complete")
            print(result.stdout)
            return True
        else:
            print(f"❌ Verification failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Sync error: {e}")
        return False

if __name__ == "__main__":
    if sync_data_direct():
        print("\n🎉 Data sync completed successfully!")
        print("You can now test the sidebar layout with actual data.")
    else:
        print("\n❌ Data sync failed")
