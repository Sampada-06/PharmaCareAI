import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_auth():
    print("Testing Authentication System...")
    
    # 1. Register
    reg_data = {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "1234567890",
        "password": "testpassword"
    }
    
    print("\n1. Testing Registration...")
    try:
        response = requests.post(f"{BASE_URL}/register", json=reg_data)
        if response.status_code == 200:
            print("✅ Registration Successful")
            print(json.dumps(response.json(), indent=2))
        elif response.status_code == 400:
            print("ℹ️ User already registered (which is fine for re-run)")
        else:
            print(f"❌ Registration Failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return

    # 2. Login
    login_data = {
        "username": "test@example.com", # OAuth2PasswordRequestForm uses 'username'
        "password": "testpassword"
    }
    
    print("\n2. Testing Login...")
    response = requests.post(f"{BASE_URL}/login", data=login_data)
    if response.status_code == 200:
        print("✅ Login Successful")
        token_data = response.json()
        token = token_data["access_token"]
        print(f"Token (first 20 chars): {token[:20]}...")
    else:
        print(f"❌ Login Failed: {response.status_code}")
        print(response.text)
        return

    # 3. Get /me
    print("\n3. Testing Protected Route /me...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    if response.status_code == 200:
        print("✅ Protected Route Accessible")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"❌ Protected Route Failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_auth()
