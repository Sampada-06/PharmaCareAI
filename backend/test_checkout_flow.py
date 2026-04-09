"""
Test checkout flow with prescription
"""
import requests
import json
import base64

BASE_URL = "http://127.0.0.1:8000"

def test_checkout_with_prescription():
    print("=" * 60)
    print("Testing Checkout Flow with Prescription")
    print("=" * 60)
    
    # Step 1: Login
    print("\n1. Logging in...")
    login_data = {
        "username": "ankitanitinchavan01@gmail.com",
        "password": "password123"  # Update if different
    }
    response = requests.post(
        f"{BASE_URL}/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return
    
    token_data = response.json()
    token = token_data.get("access_token")
    print(f"✓ Logged in successfully")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Clear cart
    print("\n2. Clearing cart...")
    requests.delete(f"{BASE_URL}/cart/clear")
    print("✓ Cart cleared")
    
    # Step 3: Get a prescription-required medicine
    print("\n3. Finding prescription-required medicine...")
    response = requests.get(f"{BASE_URL}/medicines")
    medicines = response.json()
    
    rx_medicine = None
    for med in medicines:
        if med.get("prescription_required") and med.get("stock_qty", 0) > 0:
            rx_medicine = med
            break
    
    if not rx_medicine:
        print("❌ No prescription-required medicines with stock found")
        return
    
    print(f"✓ Found: {rx_medicine['name']} (ID: {rx_medicine['id']})")
    
    # Step 4: Add to cart
    print("\n4. Adding to cart...")
    cart_data = {
        "medicine_id": rx_medicine['id'],
        "medicine_name": rx_medicine['name'],
        "price_inr": rx_medicine['price'],
        "qty": 1
    }
    
    response = requests.post(f"{BASE_URL}/cart/add", json=cart_data)
    result = response.json()
    
    if result.get('status') != 'success':
        print(f"❌ Failed to add to cart: {result}")
        return
    
    print(f"✓ Added to cart: {result.get('message')}")
    
    # Step 5: Create fake prescription (small base64 image)
    print("\n5. Creating prescription data...")
    # Tiny 1x1 pixel PNG
    fake_prescription = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    prescriptions = {
        rx_medicine['id']: fake_prescription
    }
    print("✓ Prescription data created")
    
    # Step 6: Checkout
    print("\n6. Attempting checkout...")
    checkout_data = {
        "payment_method": "COD",
        "prescriptions": prescriptions
    }
    
    response = requests.post(
        f"{BASE_URL}/checkout",
        json=checkout_data,
        headers=headers
    )
    
    print(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ CHECKOUT SUCCESSFUL!")
        print(f"  - Order ID: {result.get('order_id')}")
        print(f"  - Total: ₹{result.get('total_amount')}")
        print(f"  - Payment: {result.get('payment_method')}")
    else:
        print(f"\n❌ CHECKOUT FAILED!")
        try:
            error = response.json()
            print(f"  Error: {json.dumps(error, indent=2)}")
        except:
            print(f"  Error: {response.text}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        test_checkout_with_prescription()
    except Exception as e:
        print(f"\n❌ TEST ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
