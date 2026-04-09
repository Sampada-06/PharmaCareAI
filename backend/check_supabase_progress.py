import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

def check_counts():
    tables = ["pharmacy_products", "customer_history", "refill_alerts"]
    for table in tables:
        try:
            res = supabase.table(table).select("*", count="exact").limit(1).execute()
            print(f"Table {table}: {res.count} rows")
        except Exception as e:
            print(f"Error checking {table}: {e}")

if __name__ == "__main__":
    check_counts()
