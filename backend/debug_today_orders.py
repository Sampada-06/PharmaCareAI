import os
from datetime import datetime, timezone
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
    
    # Check for orders created today (local time)
    # 2026-02-28
    res = supabase.table("orders").select("id, user_id, created_at").gte("created_at", "2026-02-28T00:00:00Z").order("created_at", desc=True).execute()
    orders = res.data or []
    print(f"Total orders created today: {len(orders)}")
    for o in orders:
        print(f"  {o['id']} | {o['user_id']} | {o['created_at']}")

if __name__ == "__main__":
    check()
