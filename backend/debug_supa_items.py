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
    
    # Get items for order PH1772274463 (the latest one)
    res = supabase.table("order_items").select("*").eq("order_id", "PH1772274463").execute()
    items = res.data or []
    print(f"Items for PH1772274463:")
    for i in items:
        # Get product name
        p_res = supabase.table("pharmacy_products").select("product_name").eq("product_id", i['medicine_id']).limit(1).single().execute()
        p_name = p_res.data.get("product_name") if p_res.data else "Unknown"
        print(f"  {p_name} | Qty: {i['quantity']} | Price: {i['price']}")

if __name__ == "__main__":
    check()
