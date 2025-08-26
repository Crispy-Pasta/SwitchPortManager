import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    # Connect to local PostgreSQL
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=5432,
        database='port_tracer_db',
        user='dell_tracer_user',
        password='secure_password123'
    )
    
    cursor = conn.cursor()
    
    # Check site table
    cursor.execute("SELECT COUNT(*) FROM site")
    site_count = cursor.fetchone()[0]
    print(f'Sites: {site_count} records')
    
    if site_count > 0:
        cursor.execute("SELECT * FROM site LIMIT 10")
        sites = cursor.fetchall()
        print('Sample sites:')
        for site in sites:
            print('  ', site)
    
    # Check floor table
    cursor.execute("SELECT COUNT(*) FROM floor")
    floor_count = cursor.fetchone()[0]
    print(f'Floors: {floor_count} records')
    
    # Check switch table  
    cursor.execute("SELECT COUNT(*) FROM switch")
    switch_count = cursor.fetchone()[0]
    print(f'Switches: {switch_count} records')
    
    conn.close()
    
except Exception as e:
    print(f'Error: {e}')
