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
    
    # Search for anonymous orders
    res = supabase.table("orders").select("*").eq("user_id", "anonymous").execute()
    orders = res.data or []
    print(f"Found {len(orders)} anonymous orders")
    for o in orders:
        print(f"  ID: {o['id']} | Date: {o['created_at']} | Total: {o['total_amount']}")

if __name__ == "__main__":
    check()
