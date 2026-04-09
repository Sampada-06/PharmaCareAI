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
    
    # Get first 5 products from Supabase
    res = supabase.table("pharmacy_products").select("id, product_name, pzn").limit(5).execute()
    products = res.data or []
    print(f"Supabase Products:")
    for p in products:
        print(f"  {p['id']} | {p['product_name']} | {p.get('pzn')}")

if __name__ == "__main__":
    check()
