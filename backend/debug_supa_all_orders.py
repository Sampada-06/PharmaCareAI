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
    
    # Get all orders
    res = supabase.table("orders").select("id, user_id, order_status, total_amount").order("created_at", desc=True).limit(20).execute()
    orders = res.data or []
    print(f"Latest 20 orders in Supabase:")
    for o in orders:
        print(f"  ID: {o['id']} | User: {o['user_id']} | Status: {o['order_status']} | Amount: {o['total_amount']}")

if __name__ == "__main__":
    check()
