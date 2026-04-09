import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Email Configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER", "").strip() if os.getenv("EMAIL_USER") else None
EMAIL_PASS = os.getenv("EMAIL_PASS", "").strip() if os.getenv("EMAIL_PASS") else None

def send_order_confirmation_email(user_email: str, order_details: dict):
    """
    Sends an order confirmation email to the user via SMTP.
    """
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("SMTP credentials not configured. Email notification skipped.")
        return False

    try:
        # 1. Prepare Email Content
        order_id = order_details.get("order_id", "N/A")
        total_amount = order_details.get("total_amount", "0.00")
        payment_method = order_details.get("payment_method", "N/A")
        payment_status = order_details.get("payment_status", "N/A")
        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        estimated_delivery = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")

        subject = f"Order Confirmed! Your Order ID: {order_id}"
        
        # Default tracking URL for local dev
        default_tracking_url = "http://localhost:8080/user-dashboard.html"
        tracking_url = order_details.get("tracking_url", default_tracking_url)
        
        body_text = f"""
        Hello,

        Thank you for your order with PharmaCare AI! Your order has been successfully placed.

        Order Details:
        --------------------------
        Order ID: {order_id}
        Date: {order_date}
        Total Amount: ₹{total_amount}
        Payment Method: {payment_method}
        Payment Status: {payment_status}
        
        Estimated Delivery: {estimated_delivery} (3-5 business days)
        
        You can track your order status here:
        {tracking_url}

        We will notify you once your order is shipped.

        Best regards,
        PharmaCare AI Team
        """

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #2DD4BF;">Order Confirmed!</h2>
                <p>Hello,</p>
                <p>Thank you for your order with <strong>PharmaCare AI</strong>! Your order has been successfully placed.</p>
                
                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; border-bottom: 2px solid #2DD4BF; padding-bottom: 5px;">Order Details</h3>
                    <p><strong>Order ID:</strong> {order_id}</p>
                    <p><strong>Date:</strong> {order_date}</p>
                    <p><strong>Total Amount:</strong> <span style="color: #0891B2; font-weight: bold;">₹{total_amount}</span></p>
                    <p><strong>Payment Method:</strong> {payment_method}</p>
                    <p><strong>Payment Status:</strong> {payment_status}</p>
                    <p><strong>Estimated Delivery:</strong> {estimated_delivery} (3-5 business days)</p>
                </div>
                
                <div style="margin: 20px 0; text-align: center;">
                    <a href="{tracking_url}" style="background-color: #2DD4BF; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Track My Order</a>
                    <p style="font-size: 12px; color: #666; margin-top: 10px;">If the button above doesn't work, copy and paste this link into your browser:<br>{tracking_url}</p>
                </div>
                
                <p>We will notify you once your order is shipped.</p>
                <br>
                <p>Best regards,<br><strong>PharmaCare AI Team</strong></p>
            </div>
        </body>
        </html>
        """

        # 2. Setup Message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = EMAIL_USER
        message["To"] = user_email

        part1 = MIMEText(body_text, "plain")
        part2 = MIMEText(body_html, "html")
        message.attach(part1)
        message.attach(part2)

        # 3. Connect and Send
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, user_email, message.as_string())
        
        logger.info(f"Order confirmation email sent to {user_email} for Order ID: {order_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email notification to {user_email}: {e}")
        return False

def send_refill_alert_email(user_email: str, alert_data: dict):
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("SMTP credentials not configured. Email notification skipped.")
        return False

    try:
        medicine_name = alert_data.get("medicine_name", "your medicine")
        days_remaining = alert_data.get("days_remaining", 0)
        
        subject = f"Refill Reminder: {medicine_name}"
        
        body_text = f"Hello,\n\nThis is a reminder that you have approx {days_remaining} days left of {medicine_name}. Please consider refilling your prescription soon to avoid missing your doses.\n\nBest regards,\nPharmaCare AI Team"
        
        body_html = f"<html><body><h3>Refill Reminder</h3><p>Hello,</p><p>This is a reminder that you have approx <strong>{days_remaining} days left</strong> of <strong>{medicine_name}</strong>. Please consider refilling your prescription soon to avoid missing your doses.</p><p>Best regards,<br>PharmaCare AI Team</p></body></html>"
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = EMAIL_USER
        message["To"] = user_email

        part1 = MIMEText(body_text, "plain")
        part2 = MIMEText(body_html, "html")
        message.attach(part1)
        message.attach(part2)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, user_email, message.as_string())
        
        logger.info(f"Refill alert email sent to {user_email} for {medicine_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to send refill email to {user_email}: {e}")
        return False

def send_low_stock_email(pharmacist_email: str, low_stock_items: list):
    """
    Sends an alert to the pharmacist regarding low stock items.
    """
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("SMTP credentials not configured. Email notification skipped.")
        return False

    if not low_stock_items:
        return True

    try:
        subject = f"Urgent: Low Stock Alert ({len(low_stock_items)} items)"
        
        # Build plain text body
        body_text_lines = ["Hello Pharmacist,\n\nThe following items are currently low on stock in the inventory:\n"]
        for item in low_stock_items:
            body_text_lines.append(f"- {item['name']}: {item['stock_qty']} units remaining")
        body_text_lines.append("\nPlease review your inventory and reorder soon.\n\nBest regards,\nPharmaCare AI System")
        body_text = "\n".join(body_text_lines)
        
        # Build HTML body
        body_html_lines = [
            "<html><body><h3>Low Stock Alert</h3>",
            "<p>Hello Pharmacist,</p>",
            "<p>The following items are running low and require attention:</p>",
            "<ul>"
        ]
        for item in low_stock_items:
            body_html_lines.append(f"<li><strong>{item['name']}</strong>: <span style='color:red;'>{item['stock_qty']} units remaining</span></li>")
        body_html_lines.append("</ul>")
        body_html_lines.append("<p>Please review your inventory on the dashboard and reorder soon.</p>")
        body_html_lines.append("<p>Best regards,<br>PharmaCare AI System</p></body></html>")
        body_html = "\n".join(body_html_lines)
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = EMAIL_USER
        message["To"] = pharmacist_email

        part1 = MIMEText(body_text, "plain")
        part2 = MIMEText(body_html, "html")
        message.attach(part1)
        message.attach(part2)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, pharmacist_email, message.as_string())
        
        logger.info(f"Low stock alert email sent to {pharmacist_email} with {len(low_stock_items)} items")
        return True

    except Exception as e:
        logger.error(f"Failed to send low stock email to {pharmacist_email}: {e}")
        return False
