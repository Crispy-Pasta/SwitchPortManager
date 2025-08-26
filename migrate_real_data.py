import psycopg2
import subprocess

def get_local_sites():
    """Get all actual sites from local database"""
    print("🔄 Fetching actual sites from local database...")
    
    try:
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='port_tracer_db',
            user='dell_tracer_user',
            password='secure_password123'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM site ORDER BY id")
        sites = cursor.fetchall()
        conn.close()
        
        print(f"✅ Found {len(sites)} actual sites:")
        for site in sites:
            print(f"   - {site[0]}: {site[1]}")
        
        return sites
        
    except Exception as e:
        print(f"❌ Error fetching local data: {e}")
        return []

def migrate_sites_to_production(sites):
    """Migrate actual sites to production one by one"""
    print(f"\n📥 Migrating {len(sites)} sites to production...")
    
    success_count = 0
    
    for site_id, site_name in sites:
        # Escape single quotes for SQL
        safe_name = site_name.replace("'", "''")
        
        # Use subprocess with proper command structure
        cmd = [
            'ssh', 'janzen@10.50.0.225',
            f'docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c "INSERT INTO site (id, name) VALUES ({site_id}, \'{safe_name}\')"'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Migrated: {site_name}")
                success_count += 1
            else:
                print(f"❌ Failed: {site_name} - {result.stderr}")
        except Exception as e:
            print(f"❌ Error migrating {site_name}: {e}")
    
    print(f"\n🎯 Migration completed: {success_count}/{len(sites)} sites migrated successfully")
    return success_count

def verify_production_data():
    """Verify the migration was successful"""
    print("\n🔍 Verifying production data...")
    
    try:
        cmd = [
            'ssh', 'janzen@10.50.0.225',
            'docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c "SELECT id, name FROM site ORDER BY id LIMIT 10;"'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Production verification:")
            print(result.stdout)
            return True
        else:
            print(f"❌ Verification failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

if __name__ == "__main__":
    print("🌟 Dell Port Tracer - Real Data Migration")
    print("=" * 50)
    
    # Step 1: Get actual local sites
    sites = get_local_sites()
    
    if sites:
        # Step 2: Migrate to production
        success_count = migrate_sites_to_production(sites)
        
        if success_count > 0:
            # Step 3: Verify
            verify_production_data()
            print(f"\n🎉 Successfully migrated your actual site data!")
            print(f"Production now has {success_count} real sites instead of test data.")
        else:
            print("\n❌ Migration failed - no sites were transferred")
    else:
        print("\n❌ No local sites found to migrate")
