import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

SHIVA_ID = "c3481d2b-863a-496c-8b6a-a97a73f8645c"

def check():
    if not URL or not KEY:
        print("Missing credentials")
        return
    
    supabase = create_client(URL, KEY)
    
    # Get total orders
    res = supabase.table("orders").select("id, user_id, order_status").eq("user_id", SHIVA_ID).execute()
    orders = res.data or []
    print(f"Total orders for Shiva: {len(orders)}")
    for o in orders:
        print(f"  {o['id']}: {o['order_status']}")
    
    # Also check if there are any orders with 'anonymous'
    res = supabase.table("orders").select("id, user_id, order_status").eq("user_id", "anonymous").execute()
    anon_orders = res.data or []
    print(f"\nTotal anonymous orders: {len(anon_orders)}")

if __name__ == "__main__":
    check()
