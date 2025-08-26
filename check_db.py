import sqlite3

conn = sqlite3.connect('port_tracer.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

# Check each table for data
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f'{table_name}: {count} records')
    
    if count > 0 and count < 10:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
        rows = cursor.fetchall()
        print(f'Sample data from {table_name}:')
        for row in rows:
            print('  ', row)

conn.close()
