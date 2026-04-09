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
    
    # Search for user_ids matching any of Shiva's ID fragments
    res = supabase.table("orders").select("id, user_id, order_status").ilike("user_id", "%c348%").execute()
    orders = res.data or []
    print(f"Total matching orders: {len(orders)}")
    for o in orders:
        print(f"  {o['id']} | {o['user_id']} | {o['order_status']}")

if __name__ == "__main__":
    check()
