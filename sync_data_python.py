import psycopg2
import subprocess
import json

def export_local_data():
    """Export data from local PostgreSQL database using Python"""
    print("🔄 Exporting data from local database...")
    
    try:
        # Connect to local database
        local_conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='port_tracer_db',
            user='dell_tracer_user',
            password='secure_password123'
        )
        
        cursor = local_conn.cursor()
        
        # Get all site data
        cursor.execute("SELECT * FROM site")
        sites = cursor.fetchall()
        
        # Get all floor data
        cursor.execute("SELECT * FROM floor")
        floors = cursor.fetchall()
        
        # Get all switch data
        cursor.execute("SELECT * FROM switch")
        switches = cursor.fetchall()
        
        local_conn.close()
        
        print(f"✅ Exported {len(sites)} sites, {len(floors)} floors, {len(switches)} switches")
        return {'sites': sites, 'floors': floors, 'switches': switches}
        
    except Exception as e:
        print(f"❌ Export error: {e}")
        return None

def create_insert_sql(data):
    """Create SQL INSERT statements from exported data"""
    sql_statements = []
    
    # Clear existing data first
    sql_statements.extend([
        "DELETE FROM switch;",
        "DELETE FROM floor;", 
        "DELETE FROM site;"
    ])
    
    # Helper function to escape single quotes
    def escape_sql(value):
        if value is None:
            return ''
        return str(value).replace("'", "''")
    
    # Insert sites
    for site in data['sites']:
        if len(site) >= 4:  # Ensure we have enough columns
            site_name = escape_sql(site[1])
            site_code = escape_sql(site[2]) if site[2] else ''
            description = escape_sql(site[3]) if site[3] else ''
            location = escape_sql(site[4]) if len(site) > 4 and site[4] else ''
            
            sql = f"INSERT INTO site (site_id, site_name, site_code, description, location) VALUES ({site[0]}, '{site_name}', '{site_code}', '{description}', '{location}');"
            sql_statements.append(sql)
    
    # Insert floors  
    for floor in data['floors']:
        if len(floor) >= 4:
            floor_name = escape_sql(floor[2])
            description = escape_sql(floor[3]) if floor[3] else ''
            
            sql = f"INSERT INTO floor (floor_id, site_id, floor_name, description) VALUES ({floor[0]}, {floor[1]}, '{floor_name}', '{description}');"
            sql_statements.append(sql)
    
    # Insert switches (simplified - only basic columns)
    for switch in data['switches']:
        if len(switch) >= 6:
            switch_name = escape_sql(switch[3])
            ip_address = escape_sql(switch[4])
            model = escape_sql(switch[5]) if switch[5] else 'Unknown'
            
            sql = f"INSERT INTO switch (switch_id, site_id, floor_id, switch_name, ip_address, model) VALUES ({switch[0]}, {switch[1]}, {switch[2]}, '{switch_name}', '{ip_address}', '{model}');"
            sql_statements.append(sql)
    
    return sql_statements

def import_to_production(sql_statements):
    """Import data to production via SSH"""
    print("📥 Importing data to production database...")
    
    # Write SQL to temp file
    with open('import_data.sql', 'w') as f:
        for sql in sql_statements:
            f.write(sql + '\n')
    
    try:
        # Copy SQL file to production
        copy_result = subprocess.run(['scp', 'import_data.sql', 'janzen@10.50.0.225:/tmp/'], 
                                   capture_output=True, text=True)
        
        if copy_result.returncode != 0:
            print(f"❌ Failed to copy SQL file: {copy_result.stderr}")
            return False
        
        # Execute SQL on production
        exec_result = subprocess.run([
            'ssh', 'janzen@10.50.0.225',
            'docker exec -i dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -f /tmp/import_data.sql'
        ], capture_output=True, text=True)
        
        if exec_result.returncode == 0:
            print("✅ Data imported successfully to production")
            return True
        else:
            print(f"❌ Import failed: {exec_result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    print("🌟 Dell Port Tracer Data Sync (Python Version)")
    print("=" * 50)
    
    # Export local data
    data = export_local_data()
    if data:
        # Create SQL statements
        print("🔧 Creating SQL import statements...")
        sql_statements = create_insert_sql(data)
        print(f"✅ Created {len(sql_statements)} SQL statements")
        
        # Import to production
        if import_to_production(sql_statements):
            print("\n🎉 Data sync completed successfully!")
            print("Your production server now has the same test data as local.")
        else:
            print("\n❌ Failed during import")
    else:
        print("\n❌ Failed to export local data")
    
    # Clean up
    import os
    if os.path.exists('import_data.sql'):
        os.remove('import_data.sql')
