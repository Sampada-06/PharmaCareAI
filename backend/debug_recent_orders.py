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
    
    # Get last 10 orders
    res = supabase.table("orders").select("id, user_id, created_at").order("created_at", desc=True).limit(10).execute()
    orders = res.data or []
    print(f"Last 10 orders:")
    for o in orders:
        print(f"  {o['id']} | {o['user_id']} | {o['created_at']}")

if __name__ == "__main__":
    check()
