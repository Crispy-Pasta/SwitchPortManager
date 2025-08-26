#!/usr/bin/env python3
"""
Export local SQLite database data to PostgreSQL-compatible SQL format
"""
import sqlite3
import os

def export_sqlite_to_sql(db_path, output_file):
    """Export SQLite database to PostgreSQL-compatible SQL"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        
        print(f"📊 Found {len(tables)} tables in database")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- PostgreSQL Data Import Script\n")
            f.write("-- Generated from local SQLite database\n")
            f.write("-- Date: " + __import__('datetime').datetime.now().isoformat() + "\n\n")
            
            # Export each table
            for table in tables:
                table_name = table[0]
                print(f"📋 Processing table: {table_name}")
                
                # Get table data
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                if rows:
                    print(f"   📁 Found {len(rows)} records")
                    
                    # Get column names
                    columns = [description[0] for description in cursor.description]
                    
                    f.write(f"-- Table: {table_name}\n")
                    f.write(f"-- Records: {len(rows)}\n")
                    
                    # Clear existing data
                    f.write(f"DELETE FROM {table_name};\n")
                    
                    # Generate INSERT statements
                    for row in rows:
                        values = []
                        for value in row:
                            if value is None:
                                values.append('NULL')
                            elif isinstance(value, str):
                                # Escape single quotes for PostgreSQL
                                escaped_value = value.replace("'", "''")
                                values.append(f"'{escaped_value}'")
                            else:
                                values.append(str(value))
                        
                        columns_str = ', '.join(columns)
                        values_str = ', '.join(values)
                        f.write(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});\n")
                    
                    f.write(f"\n")
                    
                    # Reset sequences for PostgreSQL
                    if 'id' in columns:
                        f.write(f"-- Reset sequence for {table_name}\n")
                        f.write(f"SELECT setval('{table_name}_id_seq', (SELECT COALESCE(MAX(id), 1) FROM {table_name}));\n\n")
                else:
                    print(f"   📭 Table {table_name} is empty")
                    f.write(f"-- Table {table_name} is empty\n\n")
        
        conn.close()
        print(f"✅ Export completed successfully: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error exporting database: {e}")
        return False

if __name__ == "__main__":
    db_file = "port_tracer.db"
    output_file = "database_export.sql"
    
    print("🚀 Exporting local SQLite database to PostgreSQL format")
    print("=" * 60)
    
    success = export_sqlite_to_sql(db_file, output_file)
    
    if success:
        print("\n🎉 Database export completed!")
        print(f"📄 SQL file created: {output_file}")
        print("\nNext steps:")
        print("1. Transfer the SQL file to the production server")
        print("2. Import it into the PostgreSQL database")
    else:
        print("\n❌ Export failed!")
