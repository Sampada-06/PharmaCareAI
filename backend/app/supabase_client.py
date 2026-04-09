import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()

def check_connectivity(url, timeout=2):
    """Check if the Supabase URL is reachable quickly."""
    if not url: return False
    try:
        # Just check the base URL with a very short timeout
        requests.get(url, timeout=timeout)
        return True
    except:
        return False

def get_supabase() -> Client:
    """Returns an initialized Supabase client if reachable."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    
    # We check connectivity to prevent 60-second hangs on blocked networks
    if check_connectivity(SUPABASE_URL):
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception:
            return None
    else:
        print("⚠️ SUPABASE UNREACHABLE: Falling back to Local Mode. (Check network/VPN)")
        return None

# Singleton instance
supabase: Client = get_supabase()
