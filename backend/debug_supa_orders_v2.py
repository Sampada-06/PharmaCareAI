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
    
    # Get total orders
    res = supabase.table("orders").select("id, user_id").execute()
    orders = res.data or []
    print(f"Total orders: {len(orders)}")
    
    user_counts = {}
    for o in orders:
        uid = o.get("user_id", "None")
        user_counts[uid] = user_counts.get(uid, 0) + 1
        
    print("\nOrders per user_id:")
    for uid, count in user_counts.items():
        print(f"  {uid}: {count}")

if __name__ == "__main__":
    check()
