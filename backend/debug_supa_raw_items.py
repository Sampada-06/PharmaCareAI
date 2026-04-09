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
    
    # Get items for order PH1772274463
    res = supabase.table("order_items").select("*").eq("order_id", "PH1772274463").execute()
    items = res.data or []
    print(f"Raw items for PH1772274463:")
    for i in items:
        print(f"  {i}")

if __name__ == "__main__":
    check()
