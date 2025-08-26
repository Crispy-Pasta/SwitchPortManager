import psycopg2
import subprocess
import os

def export_local_data():
    """Export data from local PostgreSQL database"""
    print("🔄 Exporting data from local database...")
    
    # Create SQL dump file
    dump_command = [
        'pg_dump',
        '-h', '127.0.0.1',
        '-p', '5432',
        '-U', 'dell_tracer_user',
        '-d', 'port_tracer_db',
        '--data-only',
        '--no-owner',
        '--no-privileges',
        '-f', 'local_data_export.sql'
    ]
    
    # Set password environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = 'secure_password123'
    
    try:
        result = subprocess.run(dump_command, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Local data exported to local_data_export.sql")
            return True
        else:
            print(f"❌ Export failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Export error: {e}")
        return False

def copy_to_production():
    """Copy the SQL dump to production server"""
    print("🚀 Copying data to production server...")
    
    try:
        # Copy file to production server
        copy_command = ['scp', 'local_data_export.sql', 'janzen@10.50.0.225:/tmp/']
        result = subprocess.run(copy_command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Data file copied to production server")
            return True
        else:
            print(f"❌ Copy failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Copy error: {e}")
        return False

def import_to_production():
    """Import data to production PostgreSQL"""
    print("📥 Importing data to production database...")
    
    try:
        # Import data via SSH
        import_command = [
            'ssh', 'janzen@10.50.0.225',
            'docker exec -i dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db < /tmp/local_data_export.sql'
        ]
        
        result = subprocess.run(import_command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Data imported successfully to production")
            return True
        else:
            print(f"❌ Import failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    print("🌟 Dell Port Tracer Data Sync")
    print("=" * 40)
    
    # Step 1: Export local data
    if export_local_data():
        # Step 2: Copy to production
        if copy_to_production():
            # Step 3: Import to production
            if import_to_production():
                print("\n🎉 Data sync completed successfully!")
                print("Your production server now has the same test data as local.")
            else:
                print("\n❌ Failed at import step")
        else:
            print("\n❌ Failed at copy step")
    else:
        print("\n❌ Failed at export step")
    
    # Clean up
    if os.path.exists('local_data_export.sql'):
        print("\n🧹 Cleaning up temporary files...")
        os.remove('local_data_export.sql')
