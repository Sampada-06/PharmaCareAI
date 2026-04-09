import sys
import os
import logging

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from email_service import send_order_confirmation_email

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_email_logic():
    print("Testing Email Notification System...")
    
    mock_order = {
        "order_id": "PH-TEST-123",
        "total_amount": "1250.50",
        "payment_method": "UPI",
        "payment_status": "Success"
    }
    
    # Test with a dummy email
    # Note: This will fail if no real credentials are set in .env,
    # but it will verify that the failure is caught and logged correctly.
    success = send_order_confirmation_email("test@example.com", mock_order)
    
    if success:
        print("✅ Email logic test passed (Email sent successfully!)")
    else:
        print("❌ Email logic test failed or skipped (Check logs for SMTP credentials)")

if __name__ == "__main__":
    test_email_logic()
