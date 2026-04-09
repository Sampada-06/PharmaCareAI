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
    
    res = supabase.table("orders").select("*").limit(5).execute()
    if res.data:
        print(f"Order data: {res.data[0]}")
    else:
        print("No orders found")

if __name__ == "__main__":
    check()
