import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from app.email_service import send_refill_alert_email, send_low_stock_email

def test_alerts():
    # Setup test credentials
    test_email = "sampada.yanpallewar24@vit.edu"
    
    print("\n--- 1. Testing Patient Refill Alert ---")
    alert_data = {"medicine_name": "Metformin 500mg", "days_remaining": 3}
    print(f"Sending to: {test_email} | Med: {alert_data['medicine_name']} | Days Left: {alert_data['days_remaining']}")
    
    success1 = send_refill_alert_email(test_email, alert_data)
    if success1: print("SUCCESS: Refill email sent.")
    else: print("FAILED: Refill email not sent.")

    print("\n--- 2. Testing Pharmacist Low Stock Alert ---")
    low_stock_items = [
        {"name": "Paracetamol 500mg", "stock_qty": 10},
        {"name": "Amoxicillin 250mg", "stock_qty": 5}
    ]
    print(f"Sending to: {test_email} | Items: {len(low_stock_items)}")
    
    success2 = send_low_stock_email(test_email, low_stock_items)
    if success2: print("SUCCESS: Low stock email sent.")
    else: print("FAILED: Low stock email not sent.")

if __name__ == "__main__":
    test_alerts()
