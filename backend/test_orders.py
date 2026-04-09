import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_orders():
    email = "test_user_orders@example.com"
    password = "password123"
    
    # 1. Try to Login
    login_data = {"username": email, "password": password}
    try:
        response = requests.post(f"{BASE_URL}/login", data=login_data)
    except Exception as e:
        print(f"Request failed: {e}")
        return
    
    if response.status_code != 200:
        print(f"Login failed ({response.status_code}), attempting registration...")
        reg_data = {
            "name": "Order Tester",
            "email": email,
            "password": password,
            "phone": "1234567890",
            "address": "Verification Lane"
        }
        try:
            response = requests.post(f"{BASE_URL}/register", json=reg_data)
            if response.status_code != 200:
                print(f"Registration failed: {response.text}")
                return
            print("Registration successful")
            response = requests.post(f"{BASE_URL}/login", data=login_data)
            if response.status_code != 200:
                print(f"Login after registration failed: {response.text}")
                return
        except Exception as e:
            print(f"Registration request failed: {e}")
            return
            
    token_data = response.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in successfully")

    # 2. Get User ID (from /me)
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers)
        if response.status_code != 200:
            print(f"Failed to get profile: {response.text}")
            return
        user_info = response.json()
        print(f"DEBUG: /me response: {user_info}")
        user_id = user_info.get("id") or user_info.get("user_id")
        print(f"Current User ID: {user_id}")
    except Exception as e:
        print(f"Me request failed: {e}")
        return

    # 3. Get a real medicine ID
    try:
        res = requests.get(f"{BASE_URL}/medicines")
        meds = res.json()
        if not meds:
            print("No medicines found to order")
            return
        med = meds[0]
        med_id = med["id"]
        med_price = med["price"]
        med_name = med["name"]
        print(f"Test ordering: {med_name} (ID: {med_id})")
    except Exception as e:
        print(f"Failed to fetch medicines: {e}")
        return

    # 4. Create a test order
    order_data = {
        "items": [{"id": med_id, "qty": 1, "price": med_price, "name": med_name}],
        "total_amount": med_price,
        "payment_method": "COD",
        "customer_info": {"name": "Order Tester", "email": email},
        "user_id": user_id
    }
    try:
        response = requests.post(f"{BASE_URL}/orders/create", json=order_data, headers=headers)
        if response.status_code == 200:
            order_id = response.json()['order_id']
            print(f"Order created: {order_id}")
        else:
            print(f"Order creation failed: {response.text}")
            return
    except Exception as e:
        print(f"Order create request failed: {e}")
        return

    # 4. Fetch my orders
    try:
        response = requests.get(f"{BASE_URL}/orders/my", headers=headers)
        if response.status_code == 200:
            orders = response.json()
            print(f"Found {len(orders)} orders for this user")
            for o in orders:
                # Replace rupee symbol for console compatibility if needed
                status = o.get('order_status', 'N/A')
                amount = o.get('total_amount', 0)
                print(f" - {o['order_id']} | {status} | Rs.{amount}")
            
            # 5. Track the specific order
            if orders:
                track_id = orders[0]['order_id']
                track_res = requests.get(f"{BASE_URL}/orders/track/{track_id}", headers=headers)
                if track_res.status_code == 200:
                    status = track_res.json().get('order_status', 'unknown')
                    print(f"Tracking {track_id} status: {status}")
                else:
                    print(f"Tracking failed: {track_res.text}")
        else:
            print(f"Failed to fetch my orders: {response.text}")
    except Exception as e:
        print(f"Orders/my request failed: {e}")

if __name__ == "__main__":
    test_orders()
