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
    
    # Check users in Supabase
    res = supabase.table("customer_users").select("*").execute()
    users = res.data or []
    print(f"Total users in Supabase: {len(users)}")
    for u in users:
        print(f"  {u['id']} | {u['name']} | {u['email']}")

if __name__ == "__main__":
    check()
