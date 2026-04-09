import os
from dotenv import load_dotenv
from supabase import create_client
import time
from datetime import datetime, timedelta

load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

def check():
    if not URL or not KEY:
        print("Missing credentials")
        return
    
    supabase = create_client(URL, KEY)
    
    # Get any orders from today
    # PH17722...
    # PH17723...
    
    res = supabase.table("orders").select("id, user_id, order_status, total_amount, created_at").order("created_at", desc=True).limit(10).execute()
    orders = res.data or []
    print(f"Latest 10 orders:")
    for o in orders:
        print(f"  ID: {o['id']} | User: {o['user_id']} | Date: {o['created_at']} | Total: {o['total_amount']}")

if __name__ == "__main__":
    check()
