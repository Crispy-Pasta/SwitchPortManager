import sqlite3

try:
    conn = sqlite3.connect("instance/switches.db")
    cursor = conn.cursor()
    
    # Look for the specific switch by IP or name
    cursor.execute("""
    SELECT s.name, s.ip_address, s.model, s.description, st.name as site_name, f.name as floor_name
    FROM switches s 
    JOIN floors f ON s.floor_id = f.id 
    JOIN sites st ON f.site_id = st.id 
    WHERE s.ip_address = ? OR s.name LIKE ?
    """, ("10.65.0.11", "%PBCOM-F33-C1-AS-02%"))
    
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"Switch: {row[0]}")
            print(f"IP: {row[1]}")
            print(f"Model: {row[2]}")
            print(f"Description: {row[3]}")
            print(f"Site: {row[4]}")
            print(f"Floor: {row[5]}")
            print("---")
    else:
        print("No switch found with IP 10.65.0.11 or name containing PBCOM-F33-C1-AS-02")
        print("Searching all switches with similar names...")
        
        cursor.execute("""
        SELECT s.name, s.ip_address, s.model, s.description 
        FROM switches s 
        WHERE s.name LIKE ? OR s.name LIKE ? OR s.name LIKE ?
        """, ("%PBCOM%", "%F33%", "%AS-02%"))
        
        results = cursor.fetchall()
        for row in results:
            print(f"Found: {row[0]} - {row[1]} - Model: {row[2]}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
