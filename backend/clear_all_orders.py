"""
Clear All Orders - Complete Script
Clears orders from both Supabase and local SQLite database
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))
from app import models

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

def clear_all_orders():
    """Clear all orders from both Supabase and SQLite"""
    
    print("="*60)
    print("CLEAR ALL ORDERS - COMPLETE")
    print("="*60)
    print("\nThis will delete:")
    print("  1. All orders from Supabase")
    print("  2. All order items from Supabase")
    print("  3. All delivery extensions from SQLite")
    print("\n⚠️  THIS ACTION CANNOT BE UNDONE!")
    print("="*60 + "\n")
    
    # Confirm
    confirm = input("Type 'DELETE ALL' to confirm: ")
    if confirm != "DELETE ALL":
        print("❌ Deletion cancelled")
        return
    
    print("\n🗑️  Starting deletion process...\n")
    
    # ===== SUPABASE CLEANUP =====
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("✅ Connected to Supabase")
            
            # Get counts
            orders_response = supabase.table("orders").select("id", count="exact").execute()
            order_count = orders_response.count if hasattr(orders_response, 'count') else len(orders_response.data)
            
            items_response = supabase.table("order_items").select("id", count="exact").execute()
            items_count = items_response.count if hasattr(items_response, 'count') else len(items_response.data)
            
            print(f"📊 Found {order_count} orders and {items_count} order items in Supabase")
            
            if items_count > 0:
                print(f"   Deleting {items_count} order items...")
                supabase.table("order_items").delete().neq("id", "").execute()
                print(f"   ✅ Deleted order items")
            
            if order_count > 0:
                print(f"   Deleting {order_count} orders...")
                supabase.table("orders").delete().neq("id", "").execute()
                print(f"   ✅ Deleted orders")
            
            print("✅ Supabase cleanup complete\n")
            
        except Exception as e:
            print(f"❌ Supabase error: {e}\n")
    else:
        print("⚠️  Supabase credentials not found, skipping...\n")
    
    # ===== SQLITE CLEANUP =====
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        print("✅ Connected to SQLite database")
        
        # Count delivery extensions
        delivery_count = db.query(models.DeliveryExtension).count()
        print(f"📊 Found {delivery_count} delivery extensions in SQLite")
        
        if delivery_count > 0:
            print(f"   Deleting {delivery_count} delivery extensions...")
            db.query(models.DeliveryExtension).delete()
            db.commit()
            print(f"   ✅ Deleted delivery extensions")
        
        # Also clear any local Order records if they exist
        try:
            local_orders = db.query(models.Order).count()
            if local_orders > 0:
                print(f"   Deleting {local_orders} local orders...")
                db.query(models.Order).delete()
                db.commit()
                print(f"   ✅ Deleted local orders")
        except:
            pass  # Table might not exist
        
        db.close()
        print("✅ SQLite cleanup complete\n")
        
    except Exception as e:
        print(f"❌ SQLite error: {e}\n")
    
    # ===== VERIFICATION =====
    print("="*60)
    print("VERIFICATION")
    print("="*60)
    
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            verify_orders = supabase.table("orders").select("id", count="exact").execute()
            verify_items = supabase.table("order_items").select("id", count="exact").execute()
            
            orders_remaining = verify_orders.count if hasattr(verify_orders, 'count') else len(verify_orders.data)
            items_remaining = verify_items.count if hasattr(verify_items, 'count') else len(verify_items.data)
            
            print(f"Supabase orders remaining: {orders_remaining}")
            print(f"Supabase order items remaining: {items_remaining}")
            
            if orders_remaining == 0 and items_remaining == 0:
                print("✅ Supabase is clean")
            else:
                print("⚠️  Some records still remain in Supabase")
        except:
            pass
    
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        delivery_remaining = db.query(models.DeliveryExtension).count()
        print(f"SQLite delivery extensions remaining: {delivery_remaining}")
        
        if delivery_remaining == 0:
            print("✅ SQLite is clean")
        else:
            print("⚠️  Some records still remain in SQLite")
        
        db.close()
    except:
        pass
    
    print("\n" + "="*60)
    print("✅ CLEANUP COMPLETE!")
    print("="*60)
    print("\nAll order history has been cleared.")
    print("You can now start fresh with new orders.\n")

if __name__ == "__main__":
    clear_all_orders()
