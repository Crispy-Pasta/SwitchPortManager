import psycopg2
import json
import tempfile
import subprocess

def export_all_local_data():
    """Export all data from local database"""
    print("🔄 Exporting complete database from local...")
    
    try:
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='port_tracer_db',
            user='dell_tracer_user',
            password='secure_password123'
        )
        
        cursor = conn.cursor()
        
        # Export sites
        cursor.execute("SELECT * FROM site ORDER BY id")
        sites = cursor.fetchall()
        
        # Export floors
        cursor.execute("SELECT * FROM floor ORDER BY id")
        floors = cursor.fetchall()
        
        # Export switches
        cursor.execute("SELECT * FROM switch ORDER BY id")
        switches = cursor.fetchall()
        
        conn.close()
        
        data = {
            'sites': sites,
            'floors': floors,
            'switches': switches
        }
        
        print(f"✅ Exported: {len(sites)} sites, {len(floors)} floors, {len(switches)} switches")
        return data
        
    except Exception as e:
        print(f"❌ Export error: {e}")
        return None

def clear_production_database():
    """Clear all data from production database"""
    print("🧹 Clearing production database...")
    
    clear_commands = [
        "DELETE FROM switch;",
        "DELETE FROM floor;", 
        "DELETE FROM site;",
        "ALTER SEQUENCE site_id_seq RESTART WITH 1;",
        "ALTER SEQUENCE floor_id_seq RESTART WITH 1;",
        "ALTER SEQUENCE switch_id_seq RESTART WITH 1;"
    ]
    
    for cmd in clear_commands:
        try:
            result = subprocess.run([
                'ssh', 'janzen@10.50.0.225',
                f'docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c "{cmd}"'
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Clear command failed: {cmd}")
                print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing clear command: {e}")
            return False
    
    print("✅ Production database cleared")
    return True

def create_migration_sql(data):
    """Create SQL file for complete migration"""
    print("🔧 Creating migration SQL...")
    
    sql_lines = []
    
    # Disable triggers and constraints during import
    sql_lines.append("SET session_replication_role = replica;")
    
    # Import sites
    for site in data['sites']:
        site_id, site_name = site
        safe_name = site_name.replace("'", "''")
        sql_lines.append(f"INSERT INTO site (id, name) VALUES ({site_id}, '{safe_name}');")
    
    # Import floors  
    for floor in data['floors']:
        floor_id, floor_name, site_id = floor
        safe_name = floor_name.replace("'", "''")
        sql_lines.append(f"INSERT INTO floor (id, name, site_id) VALUES ({floor_id}, '{safe_name}', {site_id});")
    
    # Import switches
    for switch in data['switches']:
        switch_id, name, ip_address, model, description, enabled, floor_id = switch
        safe_name = name.replace("'", "''") if name else ''
        safe_ip = ip_address.replace("'", "''") if ip_address else ''
        safe_model = model.replace("'", "''") if model else ''
        safe_desc = description.replace("'", "''") if description else ''
        enabled_val = 'true' if enabled else 'false'
        
        sql_lines.append(f"INSERT INTO switch (id, name, ip_address, model, description, enabled, floor_id) VALUES ({switch_id}, '{safe_name}', '{safe_ip}', '{safe_model}', '{safe_desc}', {enabled_val}, {floor_id});")
    
    # Reset sequences to proper values
    sql_lines.append("SELECT setval('site_id_seq', (SELECT MAX(id) FROM site));")
    sql_lines.append("SELECT setval('floor_id_seq', (SELECT MAX(id) FROM floor));") 
    sql_lines.append("SELECT setval('switch_id_seq', (SELECT MAX(id) FROM switch));")
    
    # Re-enable triggers and constraints
    sql_lines.append("SET session_replication_role = DEFAULT;")
    
    print(f"✅ Created {len(sql_lines)} SQL statements")
    return sql_lines

def execute_migration_sql(sql_lines):
    """Execute the migration SQL on production"""
    print("📥 Executing migration on production...")
    
    # Write SQL to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
        for line in sql_lines:
            f.write(line + '\n')
        temp_file = f.name
    
    try:
        # Copy SQL file to production
        print("📤 Copying SQL file to production...")
        result = subprocess.run([
            'scp', temp_file, 'janzen@10.50.0.225:/tmp/migration.sql'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to copy SQL file: {result.stderr}")
            return False
        
        # Execute SQL file on production
        print("⚡ Executing migration SQL...")
        result = subprocess.run([
            'ssh', 'janzen@10.50.0.225',
            'docker exec -i dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -f /tmp/migration.sql'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migration executed successfully")
            print("📋 Output:", result.stdout)
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False
    finally:
        # Clean up temp file
        import os
        if os.path.exists(temp_file):
            os.unlink(temp_file)

def verify_migration():
    """Verify the complete migration"""
    print("🔍 Verifying complete migration...")
    
    tables = ['site', 'floor', 'switch']
    
    for table in tables:
        try:
            result = subprocess.run([
                'ssh', 'janzen@10.50.0.225',
                f'docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c "SELECT COUNT(*) FROM {table};"'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {table}: {result.stdout.strip()}")
            else:
                print(f"❌ Failed to verify {table}")
                
        except Exception as e:
            print(f"❌ Verification error for {table}: {e}")

def main():
    print("🌟 Dell Port Tracer - Complete Database Migration")
    print("=" * 60)
    
    # Step 1: Export all local data
    data = export_all_local_data()
    if not data:
        print("❌ Failed to export local data")
        return
    
    # Step 2: Clear production database
    if not clear_production_database():
        print("❌ Failed to clear production database")
        return
    
    # Step 3: Create migration SQL
    sql_lines = create_migration_sql(data)
    
    # Step 4: Execute migration
    if execute_migration_sql(sql_lines):
        # Step 5: Verify migration
        verify_migration()
        print("\n🎉 Complete database migration successful!")
        print("Your production database now has all your real data:")
        print(f"   - {len(data['sites'])} sites")
        print(f"   - {len(data['floors'])} floors") 
        print(f"   - {len(data['switches'])} switches")
    else:
        print("\n❌ Migration failed")

if __name__ == "__main__":
    main()
