import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

def check():
    if not URL or not KEY:
        print("Missing credentials")
        return
    
    supabase = create_client(URL, KEY)
    
    # Check for 'users' table in Supabase
    try:
        res = supabase.table("users").select("id, name, email").limit(5).execute()
        print(f"Supabase users table FOUND:")
        for u in res.data:
            print(f"  {u['id']} | {u['name']} | {u['email']}")
    except Exception as e:
        print(f"Supabase users table NOT found: {e}")

if __name__ == "__main__":
    check()
