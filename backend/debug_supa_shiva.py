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
    
    # Search for SHIVA
    shiva_id = "c3481d2b-863a-496c-8b6a-a97a73f8645c"
    res = supabase.table("orders").select("*").ilike("user_id", f"%{shiva_id[:8]}%").execute()
    orders = res.data or []
    print(f"Found {len(orders)} orders for Shiva partial match")
    for o in orders:
        print(f"  ID: {o['id']} | user_id: {o['user_id']}")

if __name__ == "__main__":
    check()
