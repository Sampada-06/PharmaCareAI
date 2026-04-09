import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from core.supabase_client import supabase
    from core.auth import get_user_profile
    print("✅ Supabase client imported successfully.")
except ImportError as e:
    print(f"❌ Failed to import Supabase components: {e}")
    sys.exit(1)

def test_supabase_setup():
    print("Testing Supabase Integration...")
    
    if supabase is None:
        print("ℹ️ Supabase client is None (likely due to missing credentials in .env)")
    else:
        print("✅ Supabase client initialized.")

    # Test get_user_profile with a dummy ID
    # Note: This will likely return None if no real DB is connected
    profile = get_user_profile("test-uuid")
    print(f"ℹ️ get_user_profile test: {'Found' if profile else 'Not found/Error (Expected for dummy ID)'}")

if __name__ == "__main__":
    test_supabase_setup()
