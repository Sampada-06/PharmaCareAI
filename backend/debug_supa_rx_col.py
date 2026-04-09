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
    
    # Get any order that has prescription_url (if the column exists)
    try:
        res = supabase.table("orders").select("id, user_id, prescription_url").not_.is_("prescription_url", "null").limit(5).execute()
        print(f"Orders with prescription_url FOUND:")
        for o in res.data:
            print(f"  {o['id']} | {o['prescription_url']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
