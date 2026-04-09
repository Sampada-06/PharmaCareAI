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
    
    # Get latest history
    res = supabase.table("customer_history").select("*").order("purchase_date", desc=True).limit(5).execute()
    data = res.data or []
    print(f"Latest history:")
    for h in data:
        print(f"  {h}")

if __name__ == "__main__":
    check()
