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
    
    # Get first 20 products
    res = supabase.table("pharmacy_products").select("id, product_id, product_name").order("id").limit(20).execute()
    for p in res.data:
        print(f"  ID: {p['id']} | ProtoID: {p['product_id']} | Name: {p['product_name']}")

if __name__ == "__main__":
    check()
