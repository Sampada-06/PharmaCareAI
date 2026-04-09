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
    
    # Check for order PH1772302869
    res = supabase.table("orders").select("*").eq("id", "PH1772302869").execute()
    if res.data:
        print(f"Order PH1772302869 FOUND: {res.data[0]}")
    else:
        print(f"Order PH1772302869 NOT found in orders table")

if __name__ == "__main__":
    check()
