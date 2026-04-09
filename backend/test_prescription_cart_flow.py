"""
Test script to verify prescription-required medicines can be added to cart
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_add_rx_medicine_to_cart():
    """Test adding a prescription-required medicine to cart"""
    
    print("=" * 60)
    print("Testing Prescription Cart Flow")
    print("=" * 60)
    
    # Step 1: Get a prescription-required medicine
    print("\n1. Fetching prescription-required medicines...")
    response = requests.get(f"{BASE_URL}/medicines")
    medicines = response.json()
    
    rx_medicine = None
    for med in medicines:
        if med.get("prescription_required"):  # Changed from requires_prescription
            rx_medicine = med
            break
    
    if not rx_medicine:
        print("❌ No prescription-required medicines found in database")
        return False
    
    print(f"✓ Found Rx medicine: {rx_medicine['name']} (ID: {rx_medicine['id']})")
    
    # Step 2: Try to add to cart
    print("\n2. Adding Rx medicine to cart...")
    cart_data = {
        "medicine_id": rx_medicine['id'],
        "medicine_name": rx_medicine['name'],
        "price_inr": rx_medicine['price'],
        "qty": 1
    }
    
    response = requests.post(f"{BASE_URL}/cart/add", json=cart_data)
    result = response.json()
    
    print(f"Full response: {json.dumps(result, indent=2)}")
    print(f"Response status: {result.get('status')}")
    print(f"Response message: {result.get('message')}")
    
    if result.get('status') == 'success':
        print("✓ Medicine added to cart successfully!")
        print(f"  - Requires prescription: {result.get('requires_prescription', False)}")
    else:
        print(f"❌ Failed to add medicine to cart")
        print(f"   Status: {result.get('status')}")
        return False
    
    # Step 3: Verify cart contains the item
    print("\n3. Verifying cart contents...")
    response = requests.get(f"{BASE_URL}/cart")
    cart = response.json()
    
    found = False
    for item in cart.get('items', []):
        if item['id'] == rx_medicine['id']:  # Changed from product_id
            found = True
            print(f"✓ Item found in cart:")
            print(f"  - Name: {item['name']}")
            print(f"  - Requires prescription: {item.get('requires_prescription', False)}")
            print(f"  - Prescription URL: {item.get('prescription_url', 'None')}")
            break
    
    if not found:
        print("❌ Item not found in cart")
        return False
    
    # Step 4: Clear cart for cleanup
    print("\n4. Cleaning up...")
    requests.delete(f"{BASE_URL}/cart/clear")
    print("✓ Cart cleared")
    
    print("\n" + "=" * 60)
    print("✅ TEST PASSED: Prescription-required medicines can be added to cart!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        test_add_rx_medicine_to_cart()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
