import requests
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
print(f"Testing connection to: {url}")

try:
    response = requests.get(url, timeout=5)
    print(f"Status Code: {response.status_code}")
    print("Connection Successful")
except Exception as e:
    print(f"Connection Failed: {e}")
