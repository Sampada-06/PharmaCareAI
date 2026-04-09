import requests
import json

API_BASE = "http://127.0.0.1:8000"

def test_chat(message):
    print(f"\nUser: {message}")
    response = requests.post(f"{API_BASE}/chat", json={"message": message})
    if response.status_code == 200:
        data = response.json()
        print(f"Bot: {data.get('message', 'No message field')}")
        if 'action' in data:
            print(f"Action: {data['action']}")
            if 'medicine_id' in data:
                print(f"Medicine ID: {data['medicine_id']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    # Test cases reported by user
    test_chat("i want to order Torrent Paracetamol 500mg 4 tablets")
    test_chat("Show me Skincare products")
    test_chat("Add Torrent Paracetamol 500mg")
