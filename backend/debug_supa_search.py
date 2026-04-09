import os
import sqlite3

UUIDs = ['029c0a14-aff8-43dd-b9ea-b35307488300', '5b22898e-cd92-465c-911c-6a3db032cd63', 'e3699146-0e19-4c34-800b-3a091d2a8da6']
DBs = [
    r"c:\Users\SAMPADA\Desktop\pharmacy-app_core_features\pharmacy-app_core_features\pharmacy-app\backend\database.db",
    r"c:\Users\SAMPADA\Desktop\pharmacy-app_core_features\pharmacy-app_core_features\pharmacy-app\backend\pharmacy.db",
    r"c:\Users\SAMPADA\Desktop\pharmacy-app_core_features\pharmacy-app_core_features\pharmacy-app\backend-node\pharmacy.db"
]

def check():
    for db_path in DBs:
        if not os.path.exists(db_path):
            print(f"Skipping {db_path} (not found)")
            continue
        
        print(f"Checking {db_path}...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cursor.fetchall()]
            print(f"  Tables: {tables}")
            
            if 'users' in tables:
                for uuid in UUIDs:
                    cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (uuid,))
                    res = cursor.fetchone()
                    if res:
                        print(f"  FOUND {uuid} in users: {res}")
                    else:
                        print(f"  {uuid} NOT found in users")
            
            conn.close()
        except Exception as e:
            print(f"  Error checking {db_path}: {e}")

if __name__ == "__main__":
    check()
