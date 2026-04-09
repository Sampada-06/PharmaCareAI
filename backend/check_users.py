"""Check what users exist"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.supabase_client import supabase

if supabase:
    # Try different table names
    for table_name in ["users", "user", "customers", "customer"]:
        try:
            response = supabase.table(table_name).select("*").limit(2).execute()
            print(f"✓ Found table: {table_name}")
            print(f"Sample data: {response.data}")
            break
        except Exception as e:
            print(f"✗ Table '{table_name}' not found: {str(e)[:50]}")
else:
    print("Supabase not initialized")
