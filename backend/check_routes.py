import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def check_routes():
    try:
        response = requests.get(f"{BASE_URL}/openapi.json")
        if response.status_code == 200:
            data = response.json()
            paths = data.get("paths", {}).keys()
            print("Available Routes:")
            for p in sorted(paths):
                print(f" - {p}")
            
            # Print specifically for our new routes
            for target in ["/register", "/login", "/me"]:
                if target in paths:
                    print(f"✅ {target} is registered")
                else:
                    print(f"❌ {target} is MISSING")
        else:
            print(f"Failed to get openapi.json: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_routes()
