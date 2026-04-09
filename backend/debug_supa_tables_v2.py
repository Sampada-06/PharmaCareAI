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
    
    # Try generic select from common tables
    tables = ["orders", "order_items", "pharmacy_products", "customer_history", "customer_users"]
    for t in tables:
        try:
            res = supabase.table(t).select("*").limit(1).execute()
            print(f"Table {t} found")
        except Exception as e:
            print(f"Table {t} NOT found: {e}")

if __name__ == "__main__":
    check()
