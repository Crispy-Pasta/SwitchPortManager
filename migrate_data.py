#!/usr/bin/env python3
"""
Data Migration Script: SQLite to PostgreSQL
============================================

Migrates existing data from the SQLite database to the new PostgreSQL database.
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def main():
    print("🔄 Starting data migration from SQLite to PostgreSQL...")
    
    try:
        # Connect to SQLite database
        print("📂 Connecting to SQLite database...")
        sqlite_conn = sqlite3.connect('instance/switches.db')
        sqlite_cursor = sqlite_conn.cursor()
        
        # Get table schema info
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = sqlite_cursor.fetchall()
        print(f"📋 Found tables in SQLite: {[table[0] for table in tables]}")
        
        # Connect to PostgreSQL
        print("🐘 Connecting to PostgreSQL database...")
        postgres_conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'port_tracer_db'),
            user=os.getenv('POSTGRES_USER', 'dell_tracer_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'secure_password123'),
            host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
        postgres_cursor = postgres_conn.cursor()
        
        # Clear existing data in PostgreSQL (to avoid conflicts)
        print("🗑️  Clearing existing data in PostgreSQL...")
        postgres_cursor.execute("DELETE FROM switch")
        postgres_cursor.execute("DELETE FROM floor")
        postgres_cursor.execute("DELETE FROM site")
        postgres_conn.commit()
        
        # Migrate sites
        print("📍 Migrating sites...")
        sqlite_cursor.execute("PRAGMA table_info(site)")
        site_columns = [col[1] for col in sqlite_cursor.fetchall()]
        print(f"   Site columns: {site_columns}")
        
        sqlite_cursor.execute("SELECT * FROM site")
        site_rows = sqlite_cursor.fetchall()
        print(f"   Found {len(site_rows)} sites to migrate")
        
        if site_rows:
            # Both SQLite and PostgreSQL have [id, name] schema
            execute_values(
                postgres_cursor,
                "INSERT INTO site (id, name) VALUES %s",
                site_rows
            )
            postgres_conn.commit()
            print(f"   ✅ Migrated {len(site_rows)} sites")
        
        # Migrate floors
        print("🏢 Migrating floors...")
        sqlite_cursor.execute("PRAGMA table_info(floor)")
        floor_columns = [col[1] for col in sqlite_cursor.fetchall()]
        print(f"   Floor columns: {floor_columns}")
        
        sqlite_cursor.execute("SELECT * FROM floor")
        floor_rows = sqlite_cursor.fetchall()
        print(f"   Found {len(floor_rows)} floors to migrate")
        
        if floor_rows:
            execute_values(
                postgres_cursor,
                "INSERT INTO floor (id, name, site_id) VALUES %s",
                floor_rows
            )
            postgres_conn.commit()
            print(f"   ✅ Migrated {len(floor_rows)} floors")
        
        # Migrate switches
        print("🔌 Migrating switches...")
        sqlite_cursor.execute("PRAGMA table_info(switch)")
        switch_columns = [col[1] for col in sqlite_cursor.fetchall()]
        print(f"   Switch columns: {switch_columns}")
        
        sqlite_cursor.execute("SELECT * FROM switch")
        switch_rows = sqlite_cursor.fetchall()
        print(f"   Found {len(switch_rows)} switches to migrate")
        
        if switch_rows:
            # Convert integer enabled column (0/1) to boolean (False/True)
            # Expected columns: [id, name, ip_address, model, description, enabled, floor_id]
            converted_switch_rows = []
            for row in switch_rows:
                # Convert row to list for modification
                row_list = list(row)
                # Convert enabled column (index 5) from integer to boolean
                if len(row_list) > 5:
                    row_list[5] = bool(row_list[5])  # Convert 0->False, 1->True
                converted_switch_rows.append(tuple(row_list))
            
            column_names = ", ".join(switch_columns)
            execute_values(
                postgres_cursor,
                f"INSERT INTO switch ({column_names}) VALUES %s",
                converted_switch_rows
            )
            postgres_conn.commit()
            print(f"   ✅ Migrated {len(switch_rows)} switches")
        
        # Verify migration
        print("\n📊 Verifying migration...")
        postgres_cursor.execute("SELECT COUNT(*) FROM site")
        site_count = postgres_cursor.fetchone()[0]
        
        postgres_cursor.execute("SELECT COUNT(*) FROM floor")
        floor_count = postgres_cursor.fetchone()[0]
        
        postgres_cursor.execute("SELECT COUNT(*) FROM switch")
        switch_count = postgres_cursor.fetchone()[0]
        
        print(f"   Sites: {site_count}")
        print(f"   Floors: {floor_count}")
        print(f"   Switches: {switch_count}")
        
        # Close connections
        sqlite_cursor.close()
        sqlite_conn.close()
        postgres_cursor.close()
        postgres_conn.close()
        
        print("\n🎉 Data migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
