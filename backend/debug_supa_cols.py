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
    
    # Get one row to see all columns
    res = supabase.table("pharmacy_products").select("*").limit(1).execute()
    if res.data:
        print(f"Columns: {res.data[0].keys()}")
        print(f"Data: {res.data[0]}")

if __name__ == "__main__":
    check()
