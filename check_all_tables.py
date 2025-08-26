import psycopg2

def check_all_local_data():
    """Check all tables and data in local database"""
    print("🔍 Analyzing local database structure and data...")
    
    try:
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='port_tracer_db',
            user='dell_tracer_user',
            password='secure_password123'
        )
        
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print(f"📊 Found {len(tables)} tables in local database:")
        
        total_records = 0
        table_data = {}
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            table_data[table_name] = count
            total_records += count
            print(f"   - {table_name}: {count} records")
        
        print(f"\n📈 Total records across all tables: {total_records}")
        
        # Show some sample data from key tables
        key_tables = ['site', 'floor', 'switch']
        for table_name in key_tables:
            if table_name in table_data and table_data[table_name] > 0:
                print(f"\n🔍 Sample data from {table_name}:")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    ORDER BY ordinal_position
                """)
                columns = [col[0] for col in cursor.fetchall()]
                print(f"   Columns: {', '.join(columns)}")
                
                for row in rows:
                    print(f"   {row}")
        
        conn.close()
        return table_data
        
    except Exception as e:
        print(f"❌ Error checking local database: {e}")
        return {}

if __name__ == "__main__":
    check_all_local_data()
