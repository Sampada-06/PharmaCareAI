import requests
import json
import uuid

BASE_URL = "http://127.0.0.1:8000"

def test_clean():
    unique_id = uuid.uuid4().hex[:6]
    email = f"user_{unique_id}@example.com"
    
    # 1. Register
    reg_data = {
        "name": f"User {unique_id}",
        "email": email,
        "phone": "1234567890",
        "password": "testpassword"
    }
    
    print(f"Testing with unique email: {email}")
    
    r = requests.post(f"{BASE_URL}/register", json=reg_data)
    if r.status_code == 200:
        print("✅ Registration OK")
    else:
        print(f"❌ Registration Failed ({r.status_code}): {r.text}")
        return

    # 2. Login
    login_data = {
        "username": email,
        "password": "testpassword"
    }
    r = requests.post(f"{BASE_URL}/login", data=login_data)
    if r.status_code == 200:
        print("✅ Login OK")
        token = r.json()["access_token"]
    else:
        print(f"❌ Login Failed ({r.status_code}): {r.text}")
        return

    # 3. Me
    r = requests.get(f"{BASE_URL}/me", headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        print("✅ /me OK")
        print(json.dumps(r.json(), indent=2))
    else:
        print(f"❌ /me Failed ({r.status_code}): {r.text}")

if __name__ == "__main__":
    test_clean()
