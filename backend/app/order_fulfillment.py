"""
Order Fulfillment System with Webhook Integration
Handles real-world actions: warehouse fulfillment, notifications, stock updates
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import requests
import time
import json
# Langfuse observe decorator (optional - for tracing)
try:
    from langfuse.decorators import observe
except ImportError:
    # Fallback if decorators not available
    def observe(name=None, **kwargs):
        def decorator(func):
            return func
        return decorator

class OrderStatus(str, Enum):
    """Order state machine states"""
    PENDING = "pending"
    PAYMENT_CONFIRMED = "payment_confirmed"
    WAREHOUSE_NOTIFIED = "warehouse_notified"
    FULFILLMENT_IN_PROGRESS = "fulfillment_in_progress"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"

class WebhookResponse(BaseModel):
    """Webhook response model"""
    success: bool
    status_code: int
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime
    retry_count: int = 0

class OrderFulfillmentRequest(BaseModel):
    """Order fulfillment request"""
    order_id: str
    items: List[Dict[str, Any]]
    customer_info: Dict[str, Any]
    total_amount: float
    payment_method: str

class NotificationRequest(BaseModel):
    """Notification request"""
    order_id: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    notification_type: str  # email, whatsapp, sms
    message: str

class OrderFulfillmentEngine:
    """
    Handles order fulfillment workflow with webhooks and notifications
    """
    
    def __init__(self):
        # Mock webhook endpoints (replace with real URLs in production)
        self.warehouse_webhook_url = "https://mock-warehouse-api.example.com/fulfill"
        self.email_webhook_url = "https://mock-email-api.example.com/send"
        self.whatsapp_webhook_url = "https://mock-whatsapp-api.example.com/send"
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        # Mock mode (for testing without real APIs)
        self.mock_mode = True
    
    # @observe(name="warehouse_fulfillment_webhook")
    def trigger_warehouse_fulfillment(
        self, 
        order_request: OrderFulfillmentRequest,
        retry_count: int = 0
    ) -> WebhookResponse:
        """
        Trigger warehouse fulfillment webhook
        
        POST /warehouse/fulfill
        {
            "order_id": "PH123",
            "items": [...],
            "customer_info": {...},
            "priority": "standard"
        }
        """
        print(f" Triggering warehouse fulfillment for order {order_request.order_id}")
        
        payload = {
            "order_id": order_request.order_id,
            "items": order_request.items,
            "customer_info": order_request.customer_info,
            "total_amount": order_request.total_amount,
            "priority": "standard",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if self.mock_mode:
                # Mock successful response
                print(f"   [MOCK] Warehouse webhook called")
                print(f"   [MOCK] Payload: {json.dumps(payload, indent=2)}")
                
                # Simulate API delay
                time.sleep(0.5)
                
                # Mock response
                mock_response = {
                    "status": "accepted",
                    "fulfillment_id": f"WH_{order_request.order_id}",
                    "estimated_ship_date": datetime.now().isoformat(),
                    "tracking_number": f"TRK{int(time.time())}"
                }
                
                return WebhookResponse(
                    success=True,
                    status_code=200,
                    response_data=mock_response,
                    timestamp=datetime.now(),
                    retry_count=retry_count
                )
            else:
                # Real API call
                response = requests.post(
                    self.warehouse_webhook_url,
                    json=payload,
                    timeout=10,
                    headers={"Content-Type": "application/json"}
                )
                
                return WebhookResponse(
                    success=response.status_code == 200,
                    status_code=response.status_code,
                    response_data=response.json() if response.ok else None,
                    timestamp=datetime.now(),
                    retry_count=retry_count
                )
                
        except Exception as e:
            error_msg = str(e)
            print(f"    Warehouse webhook failed: {error_msg}")
            
            # Retry logic
            if retry_count < self.max_retries:
                print(f"    Retrying... (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(self.retry_delay * (retry_count + 1))  # Exponential backoff
                return self.trigger_warehouse_fulfillment(order_request, retry_count + 1)
            
            return WebhookResponse(
                success=False,
                status_code=500,
                error_message=error_msg,
                timestamp=datetime.now(),
                retry_count=retry_count
            )
    
    # @observe(name="email_notification")
    def send_email_notification(
        self, 
        notification: NotificationRequest,
        retry_count: int = 0
    ) -> WebhookResponse:
        """
        Send email notification
        
        POST /email/send
        {
            "to": "customer@example.com",
            "subject": "Order Confirmation",
            "body": "..."
        }
        """
        print(f" Sending email notification for order {notification.order_id}")
        
        payload = {
            "to": notification.customer_email,
            "subject": f"Order Confirmation - {notification.order_id}",
            "body": notification.message,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if self.mock_mode:
                print(f"   [MOCK] Email sent to {notification.customer_email}")
                print(f"   [MOCK] Subject: {payload['subject']}")
                
                time.sleep(0.3)
                
                return WebhookResponse(
                    success=True,
                    status_code=200,
                    response_data={"message_id": f"EMAIL_{int(time.time())}"},
                    timestamp=datetime.now(),
                    retry_count=retry_count
                )
            else:
                response = requests.post(
                    self.email_webhook_url,
                    json=payload,
                    timeout=10
                )
                
                return WebhookResponse(
                    success=response.status_code == 200,
                    status_code=response.status_code,
                    response_data=response.json() if response.ok else None,
                    timestamp=datetime.now(),
                    retry_count=retry_count
                )
                
        except Exception as e:
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay)
                return self.send_email_notification(notification, retry_count + 1)
            
            return WebhookResponse(
                success=False,
                status_code=500,
                error_message=str(e),
                timestamp=datetime.now(),
                retry_count=retry_count
            )
    
    # @observe(name="whatsapp_notification")
    def send_whatsapp_notification(
        self, 
        notification: NotificationRequest,
        retry_count: int = 0
    ) -> WebhookResponse:
        """
        Send WhatsApp notification
        
        POST /whatsapp/send
        {
            "to": "+1234567890",
            "message": "..."
        }
        """
        print(f" Sending WhatsApp notification for order {notification.order_id}")
        
        payload = {
            "to": notification.customer_phone,
            "message": notification.message,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if self.mock_mode:
                print(f"   [MOCK] WhatsApp sent to {notification.customer_phone}")
                print(f"   [MOCK] Message: {notification.message[:50]}...")
                
                time.sleep(0.3)
                
                return WebhookResponse(
                    success=True,
                    status_code=200,
                    response_data={"message_id": f"WA_{int(time.time())}"},
                    timestamp=datetime.now(),
                    retry_count=retry_count
                )
            else:
                response = requests.post(
                    self.whatsapp_webhook_url,
                    json=payload,
                    timeout=10
                )
                
                return WebhookResponse(
                    success=response.status_code == 200,
                    status_code=response.status_code,
                    response_data=response.json() if response.ok else None,
                    timestamp=datetime.now(),
                    retry_count=retry_count
                )
                
        except Exception as e:
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay)
                return self.send_whatsapp_notification(notification, retry_count + 1)
            
            return WebhookResponse(
                success=False,
                status_code=500,
                error_message=str(e),
                timestamp=datetime.now(),
                retry_count=retry_count
            )
    
    # @observe(name="complete_order_fulfillment")
    def execute_order_fulfillment(
        self,
        order_request: OrderFulfillmentRequest,
        send_email: bool = True,
        send_whatsapp: bool = True
    ) -> Dict[str, Any]:
        """
        Complete order fulfillment workflow
        
        Steps:
        1. Trigger warehouse fulfillment webhook
        2. Log webhook response
        3. Update order status
        4. Deduct stock
        5. Send notifications (email, WhatsApp)
        
        Returns complete execution log
        """
        execution_log = {
            "order_id": order_request.order_id,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "final_status": None,
            "errors": []
        }
        
        print(f"\n{'='*70}")
        print(f" STARTING ORDER FULFILLMENT: {order_request.order_id}")
        print(f"{'='*70}\n")
        
        # Step 1: Trigger warehouse fulfillment
        print("STEP 1: Warehouse Fulfillment")
        print("-" * 70)
        warehouse_response = self.trigger_warehouse_fulfillment(order_request)
        
        execution_log["steps"].append({
            "step": "warehouse_fulfillment",
            "success": warehouse_response.success,
            "status_code": warehouse_response.status_code,
            "response": warehouse_response.response_data,
            "error": warehouse_response.error_message,
            "retry_count": warehouse_response.retry_count,
            "timestamp": warehouse_response.timestamp.isoformat()
        })
        
        if warehouse_response.success:
            print(f"    Warehouse fulfillment successful")
            print(f"    Fulfillment ID: {warehouse_response.response_data.get('fulfillment_id')}")
            print(f"    Tracking: {warehouse_response.response_data.get('tracking_number')}")
            execution_log["final_status"] = OrderStatus.WAREHOUSE_NOTIFIED
        else:
            print(f"    Warehouse fulfillment failed after {warehouse_response.retry_count} retries")
            execution_log["errors"].append("Warehouse fulfillment failed")
            execution_log["final_status"] = OrderStatus.FAILED
            return execution_log
        
        # Step 2: Send email notification
        if send_email and order_request.customer_info.get("email"):
            print(f"\nSTEP 2: Email Notification")
            print("-" * 70)
            
            email_notification = NotificationRequest(
                order_id=order_request.order_id,
                customer_email=order_request.customer_info.get("email"),
                notification_type="email",
                message=f"Your order {order_request.order_id} has been confirmed and is being processed. Tracking: {warehouse_response.response_data.get('tracking_number')}"
            )
            
            email_response = self.send_email_notification(email_notification)
            
            execution_log["steps"].append({
                "step": "email_notification",
                "success": email_response.success,
                "status_code": email_response.status_code,
                "timestamp": email_response.timestamp.isoformat()
            })
            
            if email_response.success:
                print(f"    Email sent successfully")
            else:
                print(f"    Email failed (non-critical)")
                execution_log["errors"].append("Email notification failed")
        
        # Step 3: Send WhatsApp notification
        if send_whatsapp and order_request.customer_info.get("phone"):
            print(f"\nSTEP 3: WhatsApp Notification")
            print("-" * 70)
            
            whatsapp_notification = NotificationRequest(
                order_id=order_request.order_id,
                customer_phone=order_request.customer_info.get("phone"),
                notification_type="whatsapp",
                message=f" Order {order_request.order_id} confirmed! Track: {warehouse_response.response_data.get('tracking_number')}"
            )
            
            whatsapp_response = self.send_whatsapp_notification(whatsapp_notification)
            
            execution_log["steps"].append({
                "step": "whatsapp_notification",
                "success": whatsapp_response.success,
                "status_code": whatsapp_response.status_code,
                "timestamp": whatsapp_response.timestamp.isoformat()
            })
            
            if whatsapp_response.success:
                print(f"    WhatsApp sent successfully")
            else:
                print(f"    WhatsApp failed (non-critical)")
                execution_log["errors"].append("WhatsApp notification failed")
        
        # Final summary
        execution_log["end_time"] = datetime.now().isoformat()
        execution_log["tracking_number"] = warehouse_response.response_data.get("tracking_number")
        execution_log["fulfillment_id"] = warehouse_response.response_data.get("fulfillment_id")
        
        print(f"\n{'='*70}")
        print(f" ORDER FULFILLMENT COMPLETE: {order_request.order_id}")
        print(f"   Status: {execution_log['final_status']}")
        print(f"   Tracking: {execution_log['tracking_number']}")
        print(f"   Steps completed: {len(execution_log['steps'])}")
        print(f"   Errors: {len(execution_log['errors'])}")
        print(f"{'='*70}\n")
        
        return execution_log


# Singleton instance
_fulfillment_engine = None

def get_fulfillment_engine() -> OrderFulfillmentEngine:
    """Get or create fulfillment engine instance"""
    global _fulfillment_engine
    if _fulfillment_engine is None:
        _fulfillment_engine = OrderFulfillmentEngine()
    return _fulfillment_engine
