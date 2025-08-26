import psycopg2

def create_complete_migration_sql():
    """Create a single SQL file with all migration data"""
    print("🔄 Creating complete migration SQL file...")
    
    try:
        # Connect to local database
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='port_tracer_db',
            user='dell_tracer_user',
            password='secure_password123'
        )
        
        cursor = conn.cursor()
        
        # Start building SQL file
        sql_lines = []
        
        # Clear existing data
        sql_lines.append("-- Clear existing data")
        sql_lines.append("DELETE FROM switch;")
        sql_lines.append("DELETE FROM floor;")
        sql_lines.append("DELETE FROM site;")
        sql_lines.append("")
        
        # Export and insert sites
        sql_lines.append("-- Insert sites")
        cursor.execute("SELECT id, name FROM site ORDER BY id")
        sites = cursor.fetchall()
        
        for site_id, site_name in sites:
            safe_name = site_name.replace("'", "''")
            sql_lines.append(f"INSERT INTO site (id, name) VALUES ({site_id}, '{safe_name}');")
        
        sql_lines.append("")
        
        # Export and insert floors
        sql_lines.append("-- Insert floors")
        cursor.execute("SELECT id, name, site_id FROM floor ORDER BY id")
        floors = cursor.fetchall()
        
        for floor_id, floor_name, site_id in floors:
            safe_name = floor_name.replace("'", "''")
            sql_lines.append(f"INSERT INTO floor (id, name, site_id) VALUES ({floor_id}, '{safe_name}', {site_id});")
        
        sql_lines.append("")
        
        # Export and insert switches
        sql_lines.append("-- Insert switches")
        cursor.execute("SELECT id, name, ip_address, model, description, enabled, floor_id FROM switch ORDER BY id")
        switches = cursor.fetchall()
        
        for switch_id, name, ip_address, model, description, enabled, floor_id in switches:
            safe_name = name.replace("'", "''") if name else ''
            safe_ip = ip_address.replace("'", "''") if ip_address else ''
            safe_model = model.replace("'", "''") if model else ''
            safe_desc = description.replace("'", "''") if description else ''
            enabled_val = 'true' if enabled else 'false'
            
            sql_lines.append(f"INSERT INTO switch (id, name, ip_address, model, description, enabled, floor_id) VALUES ({switch_id}, '{safe_name}', '{safe_ip}', '{safe_model}', '{safe_desc}', {enabled_val}, {floor_id});")
        
        conn.close()
        
        # Write to file
        with open('complete_migration.sql', 'w', encoding='utf-8') as f:
            for line in sql_lines:
                f.write(line + '\n')
        
        print(f"✅ Created migration file with:")
        print(f"   - {len(sites)} sites")
        print(f"   - {len(floors)} floors")
        print(f"   - {len(switches)} switches")
        print(f"   - Total: {len(sql_lines)} SQL lines")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating migration SQL: {e}")
        return False

if __name__ == "__main__":
    print("🌟 Dell Port Tracer - Simple Complete Migration")
    print("=" * 50)
    
    if create_complete_migration_sql():
        print("\n✅ Migration SQL file created: complete_migration.sql")
        print("\nNext steps:")
        print("1. Copy to production: scp complete_migration.sql janzen@10.50.0.225:/tmp/")
        print("2. Execute on production: ssh janzen@10.50.0.225 \"docker exec -i dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -f /tmp/complete_migration.sql\"")
        print("3. Verify: ssh janzen@10.50.0.225 \"docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c 'SELECT COUNT(*) FROM site; SELECT COUNT(*) FROM floor; SELECT COUNT(*) FROM switch;'\"")
    else:
        print("\n❌ Failed to create migration SQL")
