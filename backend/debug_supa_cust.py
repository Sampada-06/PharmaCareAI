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
    
    # Try generic select with customer_info
    try:
        res = supabase.table("orders").select("id, user_id, customer_info").limit(1).execute()
        print(f"Column customer_info FOUND")
    except Exception as e:
        print(f"Column customer_info NOT found: {e}")

if __name__ == "__main__":
    check()
