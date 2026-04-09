import requests
import json

API_BASE = "http://127.0.0.1:8000"

def test_chat(message):
    print(f"\nUser: {message}")
    response = requests.post(f"{API_BASE}/chat", json={"message": message})
    if response.status_code == 200:
        data = response.json()
        print(f"Bot: {data.get('message', 'No message field')}")
        # Note: In the real app, the bot message comes from the Gemini response text
        # But we want to see if it's returning the right action JSON
        if 'action' in data:
            print(f"Action: {data['action']}")
            if 'qty' in data:
                print(f"Quantity: {data['qty']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")

def check_cart():
    response = requests.get(f"{API_BASE}/cart")
    if response.status_code == 200:
        print("Cart State:", response.json())
    else:
        print("Error checking cart")

if __name__ == "__main__":
    # Clear cart first
    requests.delete(f"{API_BASE}/cart/clear")
    
    # 1. Test adding specific quantity
    test_chat("add 7 Torrent Paracetamol 500mg")
    
    # 2. Test flexible removal with quantity
    test_chat("oops i want only 5 units of paracetamol")
    
    # 3. Test clearing cart
    test_chat("get rid of everything in my cart")
