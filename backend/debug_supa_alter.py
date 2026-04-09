import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_SERVICE_KEY")

def add_col():
    if not URL or not KEY:
        print("Missing credentials")
        return
    
    # Try ALTER TABLE via a direct SQL execution if possible?
    # Supabase Python client doesn't support direct SQL unless there's an RPC.
    # But usually 'orders' table is manageable.
    print("Cannot alter table via Python SDK easily. Will try to use JSON field if possible, but it failed earlier.")

if __name__ == "__main__":
    add_col()
