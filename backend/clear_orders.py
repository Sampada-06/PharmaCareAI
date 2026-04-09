"""
Clear All Orders Script
Deletes all orders from Supabase database
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def clear_orders():
    """Clear all orders from Supabase"""
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ERROR: SUPABASE_URL or SUPABASE_KEY not found in .env file")
        return
    
    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Connected to Supabase")
        
        # Get count of orders before deletion
        orders_response = supabase.table("orders").select("id", count="exact").execute()
        order_count = orders_response.count if hasattr(orders_response, 'count') else len(orders_response.data)
        
        if order_count == 0:
            print("ℹ️  No orders found. Database is already clean.")
            return
        
        print(f"\n📊 Found {order_count} orders")
        
        # Confirm deletion
        confirm = input(f"\n⚠️  Are you sure you want to delete ALL {order_count} orders? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("❌ Deletion cancelled")
            return
        
        print("\n🗑️  Deleting orders...")
        
        # Delete all order items first (foreign key constraint)
        items_response = supabase.table("order_items").select("id", count="exact").execute()
        items_count = items_response.count if hasattr(items_response, 'count') else len(items_response.data)
        
        if items_count > 0:
            print(f"   Deleting {items_count} order items...")
            # Delete all order items
            supabase.table("order_items").delete().neq("id", "").execute()
            print(f"   ✅ Deleted {items_count} order items")
        
        # Delete all orders
        print(f"   Deleting {order_count} orders...")
        supabase.table("orders").delete().neq("id", "").execute()
        print(f"   ✅ Deleted {order_count} orders")
        
        # Verify deletion
        verify_response = supabase.table("orders").select("id", count="exact").execute()
        remaining = verify_response.count if hasattr(verify_response, 'count') else len(verify_response.data)
        
        if remaining == 0:
            print("\n✅ SUCCESS: All orders cleared from database!")
            print("   - Orders table: empty")
            print("   - Order items table: empty")
        else:
            print(f"\n⚠️  WARNING: {remaining} orders still remain")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file has correct SUPABASE_URL and SUPABASE_KEY")
        print("2. Ensure you have delete permissions in Supabase")
        print("3. Check your internet connection")

if __name__ == "__main__":
    print("="*60)
    print("CLEAR ALL ORDERS")
    print("="*60)
    print("\nThis script will delete ALL orders from the database.")
    print("This action cannot be undone!")
    print("\n" + "="*60 + "\n")
    
    clear_orders()
    
    print("\n" + "="*60)
    print("Script complete!")
    print("="*60 + "\n")
