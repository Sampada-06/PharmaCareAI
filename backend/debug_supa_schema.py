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
    
    tables = ["orders", "order_items", "pharmacy_products", "customer_history"]
    for table in tables:
        print(f"\nTable: {table}")
        try:
            res = supabase.table(table).select("*").limit(1).execute()
            if res.data:
                print(f"Columns: {res.data[0].keys()}")
            else:
                print("No data, cannot see columns via sample.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check()
