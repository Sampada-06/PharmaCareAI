"""
Check which users own which orders
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def check_orders():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ ERROR: Supabase credentials not found")
        return
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("="*60)
    print("ORDER USER MAPPING")
    print("="*60)
    
    # Get all orders
    orders_response = supabase.table("orders").select("id,user_id,total_amount,order_status,created_at").order("created_at", desc=True).execute()
    orders = orders_response.data
    
    if not orders:
        print("\nNo orders found in database")
        return
    
    print(f"\nTotal Orders: {len(orders)}\n")
    
    # Group by user_id
    user_orders = {}
    for order in orders:
        user_id = order.get("user_id", "NULL")
        if user_id not in user_orders:
            user_orders[user_id] = []
        user_orders[user_id].append(order)
    
    # Display grouped orders
    for user_id, orders_list in user_orders.items():
        print(f"\n{'='*60}")
        print(f"User ID: {user_id}")
        print(f"Order Count: {len(orders_list)}")
        print(f"{'='*60}")
        
        for order in orders_list[:5]:  # Show first 5
            print(f"  Order: {order['id']}")
            print(f"  Amount: ₹{order['total_amount']}")
            print(f"  Status: {order['order_status']}")
            print(f"  Date: {order['created_at']}")
            print()
        
        if len(orders_list) > 5:
            print(f"  ... and {len(orders_list) - 5} more orders\n")
    
    # Get users
    print(f"\n{'='*60}")
    print("REGISTERED USERS")
    print(f"{'='*60}\n")
    
    try:
        # Try to get users from Supabase auth
        # Note: This might not work depending on your Supabase setup
        print("Note: User list requires admin access to Supabase Auth")
        print("Check your Supabase dashboard → Authentication → Users")
    except:
        pass
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total Orders: {len(orders)}")
    print(f"Unique Users: {len(user_orders)}")
    print(f"\nUser IDs with orders:")
    for user_id, orders_list in user_orders.items():
        print(f"  {user_id}: {len(orders_list)} orders")
    
    print("\n" + "="*60)
    print("RECOMMENDATION")
    print("="*60)
    print("\nTo see orders in Patient Dashboard:")
    print("1. Login with the user account that placed the orders")
    print("2. Or place new orders while logged in as a patient")
    print("3. Check user_id matches between login and orders")
    print("\nTo check your current user_id:")
    print("  - Login to Patient Portal")
    print("  - Open browser console (F12)")
    print("  - Type: JSON.parse(localStorage.getItem('user')).id")
    print()

if __name__ == "__main__":
    check_orders()
