from fastapi import FastAPI, Query, HTTPException, UploadFile, File, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.language_processor import process_user_input, get_medicine_search_terms
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
import os
import sys
import re
import json
import logging
import difflib 
from datetime import datetime, timedelta
import warnings

# Suppress urllib3 and requests warnings
warnings.filterwarnings('ignore', message='urllib3.*')
warnings.filterwarnings('ignore', category=DeprecationWarning)

logger = logging.getLogger(__name__)
# import google.generativeai as genai  # Disabled
# from openai import OpenAI  # Disabled
from groq import Groq
from dotenv import load_dotenv

# Langfuse for observability (optional)
try:
    from langfuse import Langfuse, observe
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    # Create dummy decorator if langfuse not available
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if args and callable(args[0]) else decorator

# Load environment variables from multiple possible locations IMMEDIATELY
# BEFORE any internal components initialize Supabase
dotenv_paths = [
    ".env",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
]

for path in dotenv_paths:
    if os.path.exists(path):
        load_dotenv(path, override=True)

# Add current directory to path for safety_agent import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.safety_agent import get_safety_agent, SafetyDecision
from app.refill_predictor import get_refill_predictor, RefillPrediction
from app.refill_scheduler import start_scheduler, get_scheduler
from app.order_fulfillment import get_fulfillment_engine, OrderFulfillmentRequest
from app.stock_manager import get_stock_manager
from app.prescription_agent import PrescriptionValidationAgent
from app.email_service import send_order_confirmation_email
from app.core.auth import get_current_user, get_user_profile
from app import models, schemas, auth
from app.database import engine, Base, SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import or_

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
from fastapi.security import OAuth2PasswordRequestForm


from app.supabase_client import supabase

import tempfile
import time

# File paths for data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
INVENTORY_FILE = os.path.join(DATA_DIR, "pharmacy_products.csv")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.csv")
REFILL_ALERTS_FILE = os.path.join(DATA_DIR, "refill_alerts.csv")
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.csv")

MODEL_CACHE_FILE = os.path.join(tempfile.gettempdir(), "pharamacare_model_cache.txt")
BLACKLISTED_MODELS = set()

def save_model_cache(m_name):
    try:
        with open(MODEL_CACHE_FILE, "w") as f:
            f.write(m_name)
    except: pass

def clear_model_cache():
    if os.path.exists(MODEL_CACHE_FILE):
        try: os.remove(MODEL_CACHE_FILE)
        except: pass

def load_model_cache():
    if os.path.exists(MODEL_CACHE_FILE):
        try:
            with open(MODEL_CACHE_FILE, "r") as f:
                name = f.read().strip()
                # Auto-correct deprecated 'models/' prefix format
                if name.startswith('models/'):
                    name = name[len('models/'):]
                    save_model_cache(name)  # Rewrite corrected value
                return name if name not in BLACKLISTED_MODELS else None
        except: pass
    return None

# Groq Configuration
groq_api_key = os.getenv("GROQ_API_KEY", "").strip('"').strip("'").strip()
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# OpenAI/Gemini (Disabled)
openai_client = None
genai = None

# Initialize Langfuse for observability
langfuse = None
LANGFUSE_ENABLED = False

if LANGFUSE_AVAILABLE:
    langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    langfuse_host = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    if langfuse_public_key and langfuse_secret_key:
        try:
            langfuse = Langfuse(
                public_key=langfuse_public_key,
                secret_key=langfuse_secret_key,
                host=langfuse_host
            )
            LANGFUSE_ENABLED = True
        except Exception:
            langfuse = None
            LANGFUSE_ENABLED = False

# Global model state (kept for compatibility, OpenAI client used instead)
model = None

def get_model():
    """Returns Groq client."""
    global groq_client
    return groq_client

# Attempt initial setup
model = get_model()

# Structure: { medicine_id (str): { id, name, price, qty } }
_cart: dict = {}

# Structure: set of medicine_names that have passed rule-based prescription validation
_validated_prescriptions: set = set()


class CartAddRequest(BaseModel):
    medicine_id: str
    medicine_name: str
    price_inr: float
    qty: int = 1
    force_bypass_rx: bool = False

class ChatRequest(BaseModel):
    message: str
    context: dict = {}
    history: list[dict] = []

# ── Agentic AI Response Models ──────────────────────────────────────────────
class AgentIntent(BaseModel):
    """Structured intent output from Gemini Agent"""
    intent: Literal[
        "add_to_cart",
        "check_stock", 
        "place_order",
        "track_order",
        "refill_prediction",
        "cancel_order",
        "remove_from_cart",
        "clear_cart",
        "view_cart",
        "greeting",
        "find_nearby_hospitals",
        "create_order",
        "process_payment"
    ]
    medicine_name: Optional[str] = None
    medicine_id: Optional[str] = None
    quantity: Optional[int] = 1
    dosage: Optional[str] = None
    requires_prescription_check: bool = False
    order_id: Optional[str] = None
    payment_method: Optional[str] = None
    user_message_summary: Optional[str] = None
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v is not None and v < 1:
            return 1
        return v

class AgentResponse(BaseModel):
    """Final response to user after action execution"""
    success: bool
    message: str
    data: Optional[dict] = None
    action_taken: Optional[str] = None
    action: Optional[str] = None # Alias for frontend compatibility


app = FastAPI(title="PharmaCare AI API", version="2.0.0")

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup Event: Initialize All Systems ──────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Initialize all systems on startup"""
    try:
        safety_agent = get_safety_agent()
        print(f"OK: Safety Agent initialized (Database Mode)")
    except Exception as e:
        print(f"Warning: Safety Agent initialization failed: {e}")
    
    try:
        # Initialize refill predictor
        refill_predictor = get_refill_predictor()
        print(f"OK: Refill Predictor initialized")
        
        # Start background scheduler
        start_scheduler()
        print(f"OK: Refill Scheduler started (runs daily at 9:00 AM)")
    except Exception as e:
        print(f"Warning: Refill Scheduler initialization failed: {e}")
    
    try:
        # Initialize fulfillment engine
        fulfillment_engine = get_fulfillment_engine()
        print(f"OK: Order Fulfillment Engine initialized")
        
        # Initialize stock manager
        stock_manager = get_stock_manager()
        print(f"OK: Stock Manager initialized")
    except Exception as e:
        print(f"Warning: Fulfillment systems initialization failed: {e}")

    try:
        # Initialize database tables
        Base.metadata.create_all(bind=engine)
        print("OK: Database tables initialized (User table)")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")

# ── Models ───────────────────────────────────────────────────────────────────
class OrderCreateRequest(BaseModel):
    items: list
    total_amount: float
    payment_method: str
    customer_info: dict
    user_id: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    shipping_status: str
    payment_status: str = None
    rejection_reason: str = None

# ── Database Helpers ──────────────────────────────────────────────
def update_product_stock(medicine_id: int, reduce_by: int):
    if not supabase: return False
    response = supabase.table("pharmacy_products").select("stock_quantity").eq("product_id", medicine_id).limit(1).single().execute()
    if response.data:
        new_stock = response.data["stock_quantity"] - reduce_by
        supabase.table("pharmacy_products").update({"stock_quantity": new_stock}).eq("product_id", medicine_id).execute()
        return True
    return False

def save_new_order(order_data: dict, items: list):
    if not supabase: return
    # Create Order record in Supabase
    order_id = order_data["order_id"]
    new_order = {
        "id": order_id,
        "user_id": order_data.get("user_id", "anonymous"),
        "total_amount": order_data["total_amount"],
        "payment_status": order_data["payment_status"],
        "order_status": "processing"
    }
    try:
        supabase.table("orders").insert(new_order).execute()

        # Create OrderItem records in Supabase
        order_items = []
        for item in items:
            order_items.append({
                "order_id": order_id,
                "medicine_id": int(item["id"]),
                "quantity": item["qty"],
                "price": item["price"]
            })
        if order_items:
            supabase.table("order_items").insert(order_items).execute()
    except Exception as e:
        logger.error(f"Error saving order: {e}")
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {e}")

# ── Order Management Endpoints ──────────────────────────────────────────────
@app.post("/orders/create")
def create_order(request: OrderCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(auth.get_db), current_user: Optional[models.User] = Depends(auth.get_current_user_optional)):
    order_id = f"PH{int(time.time())}"
    
    # 1. Reduce stock permanently
    for item in request.items:
        update_product_stock(int(item["id"]), item["qty"])
    
    effective_user_id = str(current_user.id) if current_user else (request.user_id or "anonymous")
    
    # 2. Save order
    order_data = {
        "order_id": order_id,
        "user_id": effective_user_id,
        "total_amount": request.total_amount,
        "payment_method": request.payment_method,
        "payment_status": "Paid" if request.payment_method == "Online" else "Pending",
        "customer_info": request.customer_info,
        "timestamp": datetime.now().isoformat()
    }
    save_new_order(order_data, request.items)
    
    # Clear both global in-memory cart and database cart
    if "_cart" in globals():
        _cart.clear()
    
    if current_user:
        try:
            db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
            db.commit()
            logger.info(f"Cleared persistent cart for user {current_user.id} after order creation")
        except Exception as e:
            logger.error(f"Failed to clear persistent cart: {e}")
            db.rollback()
    
    # Send email notification in background
    user_email = current_user.email if current_user else request.customer_info.get("email")
    if user_email:
        email_data = {
            "order_id": order_id,
            "total_amount": request.total_amount,
            "payment_method": request.payment_method,
            "payment_status": "Paid" if request.payment_method == "Online" else "Pending",
            "tracking_url": f"http://localhost:5500/frontend/user-dashboard.html?track={order_id}"
        }
        background_tasks.add_task(send_order_confirmation_email, user_email, email_data)
    
    return {"status": "success", "order_id": order_id}

@app.get("/orders/my")
async def get_my_orders(current_user: models.User = Depends(auth.get_current_user)):
    if not supabase: raise HTTPException(status_code=500, detail="Supabase not initialized")
    
    user_id = str(current_user.id)
    logger.info(f"Fetching orders for user_id: {user_id}")
    
    response = supabase.table("orders").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    orders = response.data or []
    logger.info(f"Found {len(orders)} orders for user_id: {user_id}")
    
    formatted_orders = []
    for o in orders:
        items_response = supabase.table("order_items").select("*").eq("order_id", o["id"]).execute()
        raw_items = items_response.data or []
        
        formatted_items = []
        for i in raw_items:
             formatted_items.append({
                 "id": i.get("medicine_id"),
                 "qty": i.get("quantity", 1),
                 "price": i.get("price", 0)
             })
             
        formatted_orders.append({
            "order_id": o["id"],
            "total_amount": o["total_amount"],
            "payment_status": o["payment_status"],
            "order_status": o["order_status"],
            "date": o["created_at"],
            "items": formatted_items
        })
        
    return formatted_orders

@app.get("/orders/track/{order_id}")
def track_order(order_id: str, db: Session = Depends(auth.get_db)):
    if not supabase: raise HTTPException(status_code=500, detail="Supabase not initialized")
    
    response = supabase.table("orders").select("*").eq("id", order_id).single().execute()
    order = response.data
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    deliv = db.query(models.DeliveryExtension).filter(models.DeliveryExtension.order_id == order_id).first()
    delivery_timeline = {}
    if deliv:
        delivery_timeline = {
            "packed_at": deliv.packed_at.isoformat() if deliv.packed_at else None,
            "shipped_at": deliv.shipped_at.isoformat() if deliv.shipped_at else None,
            "out_for_delivery_at": deliv.out_for_delivery_at.isoformat() if deliv.out_for_delivery_at else None,
            "delivery_tomorrow_at": deliv.delivery_tomorrow_at.isoformat() if deliv.delivery_tomorrow_at else None,
            "delivered_at": deliv.delivered_at.isoformat() if deliv.delivered_at else None
        }
    
    return {
        "order_id": order["id"],
        "total_amount": order["total_amount"],
        "payment_status": order["payment_status"],
        "order_status": order["order_status"],
        "timestamp": order["created_at"],
        "delivery_status": deliv.delivery_status if deliv else "PENDING",
        "delivery_timeline": delivery_timeline,
        "rejection_reason": deliv.rejection_reason if deliv and deliv.rejection_reason else ""
    }

@app.post("/payments/generate-qr")
def generate_qr(order_id: str, amount: float):
    # Mocking a UPI QR string: upi://pay?pa=pharmacy@okaxis&pn=PharmaCare&am=XXX&tr=PHXXX
    upi_string = f"upi://pay?pa=pharmacy@okaxis&pn=PharmaCare&am={amount}&tr={order_id}"
    return {"status": "success", "qr_string": upi_string}

@app.get("/admin/orders")
def admin_get_orders(db: Session = Depends(auth.get_db)):
    if not supabase: raise HTTPException(status_code=500, detail="Supabase not initialized")
    
    # Fetch all orders
    response = supabase.table("orders").select("*").order("created_at", desc=True).execute()
    orders = response.data
    
    if not orders:
        return []
    
    # Pre-fetch all delivery extensions from SQLite
    delivery_extensions = db.query(models.DeliveryExtension).all()
    delivery_map = {ext.order_id: ext for ext in delivery_extensions}
    
    # Pre-fetch all users for customer info (batch query)
    user_ids = [o.get("user_id") for o in orders if o.get("user_id")]
    users_map = {}
    if user_ids:
        users = db.query(models.User).filter(models.User.id.in_(user_ids)).all()
        users_map = {str(u.id): {"name": u.name or "Anonymous", "email": u.email or "n/a", "phone": u.phone or "n/a"} for u in users}
    
    # Get all order IDs for batch fetching order items
    order_ids = [o["id"] for o in orders]
    
    # Batch fetch all order items for all orders
    all_items_response = supabase.table("order_items").select("*").in_("order_id", order_ids).execute()
    all_items = all_items_response.data or []
    
    # Group items by order_id
    items_by_order = {}
    medicine_ids = set()
    for item in all_items:
        order_id = item.get("order_id")
        if order_id not in items_by_order:
            items_by_order[order_id] = []
        items_by_order[order_id].append(item)
        if item.get("medicine_id"):
            medicine_ids.add(int(item.get("medicine_id")))
    
    # Batch fetch all medicine names
    medicines_map = {}
    if medicine_ids:
        medicines_response = supabase.table("pharmacy_products").select("product_id,product_name").in_("product_id", list(medicine_ids)).execute()
        medicines_map = {m["product_id"]: m["product_name"] for m in medicines_response.data}
    
    # Now build formatted orders
    formatted_orders = []
    for o in orders:
        # Get customer info
        user_id = o.get("user_id")
        customer_info = {"name": "Anonymous", "email": "n/a", "phone": "n/a"}
        
        if user_id:
            # Try customer_info JSON field first
            if o.get("customer_info"):
                try:
                    customer_info = o["customer_info"] if isinstance(o["customer_info"], dict) else json.loads(o["customer_info"])
                except:
                    pass
            # Fallback to users_map
            if customer_info["name"] == "Anonymous" and str(user_id) in users_map:
                customer_info = users_map[str(user_id)]
        
        # Get items for this order from pre-fetched data
        order_items = items_by_order.get(o["id"], [])
        formatted_items = []
        for item in order_items:
            medicine_id = item.get('medicine_id')
            medicine_name = medicines_map.get(int(medicine_id), f"Product {medicine_id}") if medicine_id else "Unknown"
            qty = item.get("quantity", 1)
            formatted_items.append({"name": medicine_name, "qty": qty})
        
        # Merge delivery data
        deliv = delivery_map.get(o["id"])
        delivery_status = deliv.delivery_status if deliv else "PENDING"
        assigned_agent_id = deliv.assigned_agent_id if deliv else None
        delivery_timeline = {
            "packed_at": deliv.packed_at.isoformat() if deliv and deliv.packed_at else None,
            "shipped_at": deliv.shipped_at.isoformat() if deliv and deliv.shipped_at else None,
            "out_for_delivery_at": deliv.out_for_delivery_at.isoformat() if deliv and deliv.out_for_delivery_at else None,
            "delivery_tomorrow_at": deliv.delivery_tomorrow_at.isoformat() if deliv and deliv.delivery_tomorrow_at else None,
            "delivered_at": deliv.delivered_at.isoformat() if deliv and deliv.delivered_at else None
        }

        formatted_orders.append({
            "order_id": o["id"],
            "total_amount": o["total_amount"],
            "payment_status": o["payment_status"],
            "shipping_status": o["order_status"],
            "timestamp": o["created_at"],
            "customer_info": json.dumps(customer_info),
            "items": json.dumps(formatted_items),
            "delivery_status": delivery_status,
            "assigned_agent_id": assigned_agent_id,
            "delivery_timeline": delivery_timeline,
            "rejection_reason": deliv.rejection_reason if deliv and deliv.rejection_reason else "",
            "prescription_url": o.get("prescription_url"),
            "prescription_required": o.get("prescription_required", False)
        })
        
    return formatted_orders

@app.patch("/admin/orders/{order_id}/status")
def admin_update_status(order_id: str, update: OrderStatusUpdate, db: Session = Depends(auth.get_db)):
    if not supabase: raise HTTPException(status_code=500, detail="Supabase not initialized")
    
    new_shipping_status = update.shipping_status
    if new_shipping_status and new_shipping_status.upper() == "APPROVED":
        new_shipping_status = "APPROVED_FOR_DELIVERY"
        
    payload = {"order_status": new_shipping_status}
    if update.payment_status:
        payload["payment_status"] = update.payment_status
        
    response = supabase.table("orders").update(payload).eq("id", order_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if update.rejection_reason or new_shipping_status.upper() == "REJECTED":
        deliv = db.query(models.DeliveryExtension).filter(models.DeliveryExtension.order_id == order_id).first()
        if not deliv:
            deliv = models.DeliveryExtension(order_id=order_id)
            db.add(deliv)
        deliv.rejection_reason = update.rejection_reason
        db.commit()
        
    return {"status": "success"}

# ═══════════════════════════════════════════════════════════════
# DELIVERY AGENCY APIs
# ═══════════════════════════════════════════════════════════════

@app.get("/api/delivery-agency/orders")
def delivery_agency_orders(db: Session = Depends(auth.get_db)):
    # Returns all delivery orders
    # Let's filter orders that are at least APPROVED_FOR_DELIVERY from admin_get_orders
    all_orders = admin_get_orders(db=db)
    delivery_states = ["APPROVED_FOR_DELIVERY", "ASSIGNED", "PACKED", "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERY_TOMORROW", "DELIVERED"]
    delivery_orders = [o for o in all_orders if o.get("shipping_status", "").upper() in delivery_states]
    return delivery_orders

@app.patch("/api/delivery-agency/orders/{order_id}/assign")
def assign_delivery_agent(order_id: str, assign_req: schemas.AgentAssignRequest, db: Session = Depends(auth.get_db)):
    if not supabase: raise HTTPException(status_code=500, detail="Supabase not initialized")
    
    deliv = db.query(models.DeliveryExtension).filter(models.DeliveryExtension.order_id == order_id).first()
    if not deliv:
        deliv = models.DeliveryExtension(order_id=order_id)
        db.add(deliv)
        
    deliv.assigned_agent_id = assign_req.agent_id
    deliv.delivery_status = "ASSIGNED"
    db.commit()
    
    # Also update Supabase state machine
    supabase.table("orders").update({"order_status": "ASSIGNED"}).eq("id", order_id).execute()
    
    return {"success": True, "message": "Agent assigned successfully"}

@app.patch("/api/delivery-agency/orders/{order_id}/status")
def update_delivery_status(order_id: str, status_update: schemas.DeliveryStatusUpdate, db: Session = Depends(auth.get_db)):
    if not supabase: raise HTTPException(status_code=500, detail="Supabase not initialized")
    
    new_status = status_update.delivery_status.upper()
    deliv = db.query(models.DeliveryExtension).filter(models.DeliveryExtension.order_id == order_id).first()
    if not deliv:
        deliv = models.DeliveryExtension(order_id=order_id)
        db.add(deliv)
        
    deliv.delivery_status = new_status
    now = datetime.utcnow()
    
    # Update timeline
    if new_status == "PACKED": deliv.packed_at = now
    elif new_status == "SHIPPED": deliv.shipped_at = now
    elif new_status == "OUT_FOR_DELIVERY": deliv.out_for_delivery_at = now
    elif new_status == "DELIVERY_TOMORROW": deliv.delivery_tomorrow_at = now
    elif new_status == "DELIVERED": deliv.delivered_at = now
    
    db.commit()
    
    # Also update Supabase state machine
    payload = {"order_status": new_status}
    if new_status == "DELIVERED":
        payload["payment_status"] = "Success"
    supabase.table("orders").update(payload).eq("id", order_id).execute()
    
    return {"success": True, "message": f"Status updated to {new_status}"}

# ═══════════════════════════════════════════════════════════════
# ADMIN DASHBOARD APIs
# ═══════════════════════════════════════════════════════════════

@app.get("/api/admin/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overview statistics for admin dashboard"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Supabase not initialized")
        
        # Get inventory count from Supabase
        inventory_response = supabase.table("pharmacy_products").select("product_id", count="exact").execute()
        total_inventory = inventory_response.count if hasattr(inventory_response, 'count') else 0
        
        # Get low stock items (stock < 50)
        low_stock_response = supabase.table("pharmacy_products").select("product_id", count="exact").lt("stock_quantity", 50).execute()
        low_stock_items = low_stock_response.count if hasattr(low_stock_response, 'count') else 0
        
        # Get total orders from Supabase
        orders_response = supabase.table("orders").select("id", count="exact").execute()
        total_orders = orders_response.count if hasattr(orders_response, 'count') else 0
        
        # Get pending prescriptions (orders that require prescription but don't have one)
        pending_rx_response = supabase.table("orders").select("id", count="exact").eq("prescription_required", True).is_("prescription_url", "null").execute()
        pending_prescriptions = pending_rx_response.count if hasattr(pending_rx_response, 'count') else 0
        
        # Get active refill alerts from local DB
        active_refill_alerts = db.query(models.RefillAlert).filter(models.RefillAlert.status == 'pending').count()
        
        # Calculate total revenue from Supabase orders
        revenue_response = supabase.table("orders").select("total_amount").execute()
        total_revenue = sum(float(order.get("total_amount", 0)) for order in revenue_response.data if order.get("total_amount"))

        return {
            "success": True,
            "data": {
                "total_inventory": total_inventory,
                "low_stock_items": low_stock_items,
                "pending_prescriptions": pending_prescriptions,
                "total_orders": total_orders,
                "active_refill_alerts": active_refill_alerts,
                "total_revenue": float(total_revenue),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/admin/inventory/all")
def get_all_inventory(db: Session = Depends(get_db)):
    """Get complete inventory with stock levels"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Supabase not initialized")
        
        # Fetch all products from Supabase
        response = supabase.table("pharmacy_products").select("*").execute()
        medicines = response.data
        
        inventory_list = []
        for m in medicines:
            stock_qty = m.get("stock_quantity", 0)
            inventory_list.append({
                "id": str(m.get("product_id")),
                "name": m.get("product_name"),
                "category": m.get("category"),
                "price": m.get("price_inr"),
                "stock_quantity": stock_qty,
                "stock_status": "out" if stock_qty == 0 else "low" if stock_qty < 50 else "ok",
                "description": m.get("description", ""),
                "prescription_needed": "yes" if m.get("requires_prescription") else "no"
            })

        return {
            "success": True,
            "data": inventory_list,
            "count": len(inventory_list)
        }
    except Exception as e:
        logger.error(f"Inventory error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/admin/inventory/low-stock")
def get_low_stock_items(threshold: int = 50, db: Session = Depends(get_db)):
    """Get items with low stock"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Supabase not initialized")
        
        # Fetch low stock items from Supabase
        response = supabase.table("pharmacy_products").select("*").lt("stock_quantity", threshold).order("stock_quantity").execute()
        low_stock = response.data

        inventory_list = []
        for m in low_stock:
            stock_qty = m.get("stock_quantity", 0)
            inventory_list.append({
                "id": str(m.get("product_id")),
                "name": m.get("product_name"),
                "category": m.get("category"),
                "price": m.get("price_inr"),
                "stock_quantity": stock_qty,
                "stock_status": "out" if stock_qty == 0 else "low"
            })

        return {
            "success": True,
            "data": inventory_list,
            "count": len(inventory_list),
            "threshold": threshold
        }
    except Exception as e:
        logger.error(f"Low stock error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/admin/orders/all")
def get_all_orders(limit: int = None, db: Session = Depends(get_db)):
    """Get all orders with details"""
    try:
        # Use the existing admin_get_orders function which has all the proper data
        orders_list = admin_get_orders(db=db)
        
        # Apply limit if specified
        if limit:
            orders_list = orders_list[:limit]

        return {
            "success": True,
            "data": orders_list,
            "count": len(orders_list)
        }
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/admin/orders/by-status")
def get_orders_by_status(status: str = None, db: Session = Depends(get_db)):
    """Get orders filtered by status"""
    try:
        # Get all orders using admin_get_orders
        all_orders = admin_get_orders(db=db)
        
        # Filter by status if provided
        if status:
            orders_list = [o for o in all_orders if o.get("shipping_status", "").upper() == status.upper()]
        else:
            orders_list = all_orders

        return {
            "success": True,
            "data": orders_list,
            "count": len(orders_list),
            "filter": status
        }
    except Exception as e:
        logger.error(f"Error fetching orders by status: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/admin/refill-alerts/all")
def get_all_refill_alerts(db: Session = Depends(get_db)):
    """Get all refill alerts for admin dashboard"""
    try:
        alerts = db.query(models.RefillAlert).filter(models.RefillAlert.status == 'pending').all()
        
        alerts_list = []
        for a in alerts:
            alerts_list.append({
                "alert_id": a.id,
                "patient_id": a.user_id,
                "medicine_name": a.medicine_name,
                "days_remaining": a.days_remaining,
                "exhaustion_date": a.exhaustion_date.strftime('%Y-%m-%d') if a.exhaustion_date else None,
                "status": a.status,
                "priority": a.priority,
                "confidence_score": a.confidence_score
            })

        return {
            "success": True,
            "data": alerts_list,
            "count": len(alerts_list)
        }
    except Exception as e:
        logger.error(f"Error fetching refill alerts: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/admin/refill-alerts/by-patient")
def get_refill_alerts_by_patient(patient_id: str, db: Session = Depends(get_db)):
    """Get refill alerts for specific patient"""
    try:
        alerts = db.query(models.RefillAlert).filter(
            models.RefillAlert.user_id == patient_id,
            models.RefillAlert.status == 'pending'
        ).all()

        alerts_list = []
        for a in alerts:
            alerts_list.append({
                "alert_id": a.id,
                "patient_id": a.user_id,
                "medicine_name": a.medicine_name,
                "days_remaining": a.days_remaining,
                "exhaustion_date": a.exhaustion_date.strftime('%Y-%m-%d') if a.exhaustion_date else None,
                "status": a.status,
                "priority": a.priority
            })

        return {
            "success": True,
            "data": alerts_list,
            "count": len(alerts_list),
            "patient_id": patient_id
        }
    except Exception as e:
        logger.error(f"Error fetching patient refill alerts: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/admin/analytics/revenue")
def get_revenue_analytics(days: int = 30, db: Session = Depends(get_db)):
    """Get revenue analytics for specified period"""
    try:
        orders = db.query(models.Order).all()

        total_revenue = sum(o.total_amount for o in orders if o.total_amount)
        total_orders = len(orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

        return {
            "success": True,
            "data": {
                "total_revenue": float(total_revenue),
                "total_orders": total_orders,
                "avg_order_value": float(avg_order_value),
                "period_days": days
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/admin/reservations/active")
def get_active_reservations():
    """Get active cart reservations (items in user carts)"""
    try:
        # For now, return mock data since we don't persist carts
        # In production, this would query a carts table
        return {
            "success": True,
            "data": [],
            "count": 0,
            "note": "Cart reservations are session-based and not persisted"
        }
    except Exception as e:
        logger.error(f"Error fetching reservations: {e}")
        return {"success": False, "error": str(e)}


# ── Refill Alert Endpoints ──────────────────────────────────────────────────
@app.get("/admin/refill-alerts")
def get_refill_alerts(db: Session = Depends(get_db)):
    """Get all refill alerts for admin dashboard"""
    try:
        predictor = get_refill_predictor()
        alerts = predictor.get_active_alerts(db)
        
        return {
            "status": "success",
            "count": len(alerts),
            "alerts": [
                {
                    "patient_id": a.user_id,
                    "medicine_name": a.medicine_name,
                    "days_remaining": a.days_remaining,
                    "exhaustion_date": a.estimated_exhaustion_date.strftime('%Y-%m-%d'),
                    "last_purchase": a.last_purchase_date.strftime('%Y-%m-%d'),
                    "quantity_purchased": a.quantity_purchased,
                    "daily_consumption": a.daily_consumption,
                    "confidence_score": a.confidence_score,
                    "alert_message": a.alert_message
                }
                for a in alerts
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "alerts": []}

@app.get("/admin/refill-alerts/{patient_id}")
def get_patient_refill_alerts(patient_id: str, db: Session = Depends(get_db)):
    """Get refill alerts for a specific patient"""
    try:
        predictor = get_refill_predictor()
        predictions = predictor.predict_refills_for_user(db, patient_id)
        alerts = [p for p in predictions if p.alert_triggered]
        
        return {
            "status": "success",
            "patient_id": patient_id,
            "count": len(alerts),
            "alerts": [
                {
                    "medicine_name": a.medicine_name,
                    "days_remaining": a.days_remaining,
                    "exhaustion_date": a.estimated_exhaustion_date.strftime('%Y-%m-%d'),
                    "alert_message": a.alert_message
                }
                for a in alerts
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "alerts": []}

@app.post("/admin/refill-check/run")
def trigger_refill_check():
    """Manually trigger refill check (for testing)"""
    try:
        scheduler = get_scheduler()
        scheduler.run_now()
        return {"status": "success", "message": "Refill check completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/refill-predictions/{patient_id}")
def get_user_predictions(patient_id: str, db: Session = Depends(get_db)):
    """Get all refill predictions for a user (including non-urgent ones)"""
    try:
        predictor = get_refill_predictor()
        predictions = predictor.predict_refills_for_user(db, patient_id)
        
        return {
            "status": "success",
            "patient_id": patient_id,
            "predictions": [
                {
                    "medicine_name": p.medicine_name,
                    "days_remaining": p.days_remaining,
                    "exhaustion_date": p.estimated_exhaustion_date.strftime('%Y-%m-%d'),
                    "daily_consumption": p.daily_consumption,
                    "alert_triggered": p.alert_triggered,
                    "confidence_score": p.confidence_score
                }
                for p in predictions
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── Shared Database ──────────────────────────────────────────────────────────
# All data is now managed via shared SQLite database using SQLAlchemy sessions.
# CSV files are kept only for historical reference and initial migration.

# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_units(pkg_str: str) -> int:
    if not pkg_str or pkg_str != pkg_str: return 1 # Handle None or NaN
    match = re.search(r'(\d+)', str(pkg_str))
    return int(match.group(1)) if match else 1

def check_interactions(cart_items):
    """
    Dynamically checks for interactions based on the 'drug_interactions' string in pharmacy_products.csv.
    """
    warnings = []
    total_score = 0

    try:
        if not supabase: return {"total_risk_score": 0, "risk_category": "Low", "warnings": []}
        
        for item in cart_items:
            # Get full record from Supabase
            response = supabase.table("pharmacy_products").select("product_name, drug_interactions").eq("product_id", int(item["id"])).limit(1).single().execute()
            product = response.data
            if not product: continue
            interaction_text = str(product.get("drug_interactions") or "").lower()
            
            if "not applicable" in interaction_text or "no major" in interaction_text:
                continue

            # Check if interaction text mentions any other product in cart by name
            for other in cart_items:
                if item["id"] == other["id"]: continue
                
                if str(other.get("name") or "").lower() in interaction_text:
                    warnings.append({
                        "medicine_1": item["name"],
                        "medicine_2": other["name"],
                        "interaction": interaction_text,
                        "risk_level": "moderate"
                    })
                    total_score += 5
    finally:
        pass

    return {
        "total_risk_score": total_score,
        "risk_category": ("High" if total_score >= 10 else "Medium" if total_score >= 5 else "Low"),
        "warnings": warnings
    }

def calculate_health_risk():
    cart_items = list(_cart.values())
    interaction_data = check_interactions(cart_items)
    interaction_score = interaction_data["total_risk_score"]

    # Advanced Score: Interaction + Prescription count + Total Item Count
    rx_score = 0
    try:
        if not supabase: return 0
        for item in cart_items:
            response = supabase.table("pharmacy_products").select("requires_prescription").eq("product_id", int(item["id"])).limit(1).single().execute()
            product = response.data
            if product and product.get("requires_prescription"):
                rx_score += 3
    finally:
        pass
            
    count_score = len(cart_items) * 1
    total_score = interaction_score + rx_score + count_score

    if total_score >= 15:
        category = "HIGH"
    elif total_score >= 8:
        category = "MEDIUM"
    else:
        category = "LOW"

    return {
        "health_risk_index": total_score,
        "risk_category": category,
        "interaction_component": interaction_score,
        "rx_component": rx_score,
        "item_count_component": count_score,
        "recommendation": "Consult pharmacist." if category == "HIGH" else "Safe to proceed."
    }

def search_medicines(
    db: Session,
    search: str = "",
    category: str = "",
    rx: str = "",
    in_stock: str = "",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: str = "",
):
    # If supabase is not initialized, fallback to old logic or error
    if not supabase:
        print("WARNING: Supabase not initialized, cannot search medicines")
        return []

    query = supabase.table("pharmacy_products").select("*")

    if search:
        # Supabase doesn't support complex OR filters easily via simple query builder
        # but we can chain filters. For complex search, we might need multiple columns
        query = query.or_(f"product_name.ilike.*{search}*,description.ilike.*{search}*,category.ilike.*{search}*")


    if category:
        query = query.ilike("category", category)

    if rx:
        if rx == "yes":
            query = query.eq("requires_prescription", True)
        elif rx == "no":
            query = query.eq("requires_prescription", False)

    if in_stock == "true":
        query = query.gt("stock_quantity", 0)

    if min_price is not None:
        query = query.gte("price", min_price)
    
    if max_price is not None:
        query = query.lte("price", max_price)

    if sort == "asc":
        query = query.order("price", ascending=True)
    elif sort == "desc":
        query = query.order("price", ascending=False)

    # Ensure large result sets don't fail parsing by applying a fixed limit
    query = query.limit(100)
    print(f"DEBUG: search='{search}', category='{category}', rx='{rx}', in_stock='{in_stock}', min_price={min_price}, max_price={max_price}, sort='{sort}'")
    
    response = query.execute()
    
    return [
        {
            "id": str(m["product_id"]),
            "name": m["product_name"],
            "category": m["category"],
            "price": m["price"],
            "stock_qty": m["stock_quantity"],
            "prescription_required": m["requires_prescription"],
            "description": m["description"],
            "drug_interactions": m["drug_interactions"]
        } for m in response.data
    ]

@app.get("/medicines")
def get_medicines(
    search: str = Query(default="", description="Search by name or description"),
    category: str = Query(default="", description="Filter by category (if available)"),
    rx: str = Query(default="", description="Filter: 'yes'|'no' (if available)"),
    in_stock: str = Query(default="", description="Filter: 'true'|'false' (if available)"),
    min_price: Optional[float] = Query(default=None, description="Minimum price filter"),
    max_price: Optional[float] = Query(default=None, description="Maximum price filter"),
    sort: str = Query(default="", description="Sort by price: 'asc' or 'desc'"),
    db: Session = Depends(auth.get_db)
):
    return search_medicines(db, search, category, rx, in_stock, min_price, max_price, sort)


@app.get("/medicines/{medicine_id}")
def get_medicine(medicine_id: int, db: Session = Depends(auth.get_db)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not initialized")
        
    response = supabase.table("pharmacy_products").select("*").eq("product_id", medicine_id).limit(1).single().execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Medicine not found")
        
    m = response.data
    return {
        "id": str(m["product_id"]),
        "name": m["product_name"],
        "category": m["category"],
        "price": m["price"],
        "stock_qty": m["stock_quantity"],
        "prescription_required": m["requires_prescription"],
        "description": m["description"],
        "drug_interactions": m["drug_interactions"]
    }


@app.get("/categories")
def get_categories(db: Session = Depends(auth.get_db)):
    if not supabase:
        return {"categories": []}
        
    # Supabase unique values for category
    response = supabase.table("pharmacy_products").select("category").execute()
    categories = list(set([m["category"] for m in response.data if m.get("category")]))
    return {"categories": sorted(categories)}


# ── Cart endpoints ─────────────────────────────────────────────────────────────

@app.post("/cart/add")
def cart_add(item: CartAddRequest, db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    mid = int(item.medicine_id)

    # ── Safety check: look up medicine in catalogue ─────────────────────────
    if not supabase: raise HTTPException(status_code=500, detail="Supabase not initialized")
    response = supabase.table("pharmacy_products").select("*").eq("product_id", mid).limit(1).single().execute()
    medicine = response.data
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    # ── Rule 0.1: Stock Check ──────────────────────────────────────────────
    if medicine.get("stock_quantity", 0) <= 0:
        return {
            "status": "refused",
            "message": "This medicine is currently out of stock.",
            "type": "out_of_stock"
        }

    # ── Rule 1: Prescription required (allow add, flag for later) ──────────
    requires_prescription = medicine.get("requires_prescription") is True

    # ── Rule 2: Antibiotic duplication ──────────────────────────────────────
    if medicine.get("category") == "Antibiotic":
        existing_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
        for cart_entry in existing_items:
            # We check the category of existing items
            resp = supabase.table("pharmacy_products").select("category").eq("product_id", cart_entry.medicine_id).limit(1).single().execute()
            if resp.data and resp.data.get("category") == "Antibiotic":
                return {
                    "status":  "warning",
                    "message": "Multiple antibiotics detected. Please consult a pharmacist.",
                }

    # ── Safe: add to cart (DB Persistence) ─────────────────────────────────
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.medicine_id == mid
    ).first()

    price = float(medicine.get("price") or 0)
    
    if cart_item:
        cart_item.quantity += item.qty
        cart_item.price = price # Update price just in case
    else:
        cart_item = models.CartItem(
            user_id=current_user.id,
            medicine_id=mid,
            quantity=item.qty,
            price=price
        )
        db.add(cart_item)
    
    db.commit()
    db.refresh(cart_item)

    return {
        "status":   "success",
        "message":  "Added to cart" + (" (Prescription required)" if requires_prescription else ""),
        "id":       str(cart_item.medicine_id),
        "name":     medicine["product_name"],
        "price":    cart_item.price,
        "qty":      cart_item.quantity,
        "subtotal": round(cart_item.price * cart_item.quantity, 2),
        "requires_prescription": requires_prescription
    }



@app.post("/cart/set-dosage")
def set_dosage(medicine_id: str, dosage_per_day: int, db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    mid = int(medicine_id)
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.medicine_id == mid
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Not in cart")

    if dosage_per_day <= 0:
        raise HTTPException(status_code=400, detail="Invalid dosage")

    cart_item.dosage_per_day = dosage_per_day
    db.commit()

    return {
        "status": "success",
        "message": f"Dosage updated to {dosage_per_day} per day"
    }


@app.post("/checkout", response_model=schemas.CheckoutResponse)
def checkout(request: schemas.CheckoutRequest, background_tasks: BackgroundTasks, db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    """
    Finalize checkout: Validate stock, simulate payment, create order, deduct stock, and clear cart.
    """
    # 1. Fetch persistent cart items
    current_cart_items_db = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    if not current_cart_items_db:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Map database items to the format expected by the rest of the checkout logic
    current_cart_items = []
    for item in current_cart_items_db:
        # We might need medicine name for fulfillment/email
        product_name = "Unknown"
        if supabase:
            try:
                res = supabase.table("pharmacy_products").select("product_name").eq("product_id", item.medicine_id).limit(1).single().execute()
                if res.data: product_name = res.data.get("product_name", "Unknown")
            except: pass
            
        current_cart_items.append({
            "id": str(item.medicine_id),
            "name": product_name,
            "price": item.price,
            "qty": item.quantity,
            "dosage_per_day": item.dosage_per_day
        })

    total_amount = sum(item['price'] * item['qty'] for item in current_cart_items)
    
    # Check if any items require prescription
    requires_prescription = False
    prescription_url = None
    
    for item in current_cart_items:
        if supabase:
            try:
                response = supabase.table("pharmacy_products").select("requires_prescription").eq("product_id", int(item["id"])).limit(1).single().execute()
                if response.data and response.data.get("requires_prescription"):
                    requires_prescription = True
                    # Get prescription from request
                    if request.prescriptions and item["id"] in request.prescriptions:
                        prescription_url = request.prescriptions[item["id"]]
                        
                        # MEDICAL SAFETY CHECK: Ensure the prescription was actually validated
                        # This bridges the gap between client-side upload and server-side order
                        m_name = (item.get("name") or "").lower().strip()
                        if m_name and m_name != "unknown" and m_name not in _validated_prescriptions:
                            # If not in our session-level validation set, we force re-validation or reject
                            logger.warning(f"Prescription for {m_name} was uploaded but not validated in this session.")
                            # For better UX, we'll allow it if it looks like it was recently uploaded, 
                            # but let's be strict as requested.
                            raise HTTPException(
                                status_code=400, 
                                detail=f"Your prescription for {m_name} has not been verified yet. Please re-upload it in the cart for automatic validation."
                            )
                    break
            except:
                pass
    
    # 1. Validate stock availability
    stock_manager = get_stock_manager()
    availability = stock_manager.check_stock_availability(current_cart_items)
    if not availability["all_available"]:
        insufficient = availability["insufficient_items"]
        names = [i["name"] for i in insufficient]
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient stock for: {', '.join(names)}"
        )

    # 2. Simulate Payment & Order Creation
    order_id = f"PH{int(time.time())}"
    payment_status = "Success" if request.payment_method != "COD" else "Pending"
    transaction_id = f"TXN{int(time.time())}" if request.payment_method == "UPI" else None
    
    # 3. Create Payment Record (Supabase)
    if not supabase: raise HTTPException(status_code=500, detail="Supabase not initialized")
    
    user_id = str(current_user.id)
    user_name = current_user.name
    user_email = current_user.email
    user_phone = current_user.phone

    try:
        supabase.table("customer_history").insert({ 
            "patient_id": user_id,
            "purchase_date": datetime.now().isoformat(),
            "product_name": "Order: " + order_id,
            "dosage_frequency": "Bundle",
            "quantity": len(current_cart_items),
            "total_price_eur": total_amount
        }).execute()
    except Exception as e:
        logger.error(f"Failed to record customer history: {e}")

    # 4. Persist Order to Supabase with prescription data
    try:
        new_order_data = {
            "order_id": order_id,
            "user_id": user_id,
            "total_amount": total_amount,
            "payment_method": request.payment_method,
            "payment_status": payment_status,
            "prescription_url": prescription_url,
            "prescription_required": requires_prescription,
            "customer_info": {
                "name": user_name,
                "email": user_email,
                "phone": user_phone
            },
            "timestamp": datetime.now().isoformat()
        }
        save_new_order(new_order_data, current_cart_items)
    except Exception as e:
        logger.error(f"Failed to persist order to Database: {e}")

    # 5. Trigger fulfillment (Warehouse/Notifications)
    try:
        fulfillment_engine = get_fulfillment_engine()
        fulfillment_request = OrderFulfillmentRequest(
            order_id=order_id,
            items=current_cart_items,
            customer_info={
                "name": user_name,
                "email": user_email,
                "phone": user_phone
            },
            total_amount=total_amount,
            payment_method=request.payment_method
        )
        fulfillment_engine.execute_order_fulfillment(fulfillment_request)
    except Exception as e:
        print(f"ERROR: Fulfillment engine error: {e}")

    # 6. Permanently deduct stock
    try:
        stock_manager.deduct_stock(current_cart_items, order_id)
    except Exception as e:
        logger.error(f"Failed to deduct stock: {e}")

    # 7. Clear the cart from DB
    try:
        db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
        db.commit()
    except Exception as e:
        logger.error(f"Failed to clear cart: {e}")

    # 8. Send Order Confirmation Email in Background
    try:
        email_data = {
            "order_id": order_id,
            "total_amount": total_amount,
            "payment_method": request.payment_method,
            "payment_status": payment_status,
            "tracking_url": f"http://localhost:8080/user-dashboard.html?track={order_id}"
        }
        background_tasks.add_task(send_order_confirmation_email, user_email, email_data)
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")

    return schemas.CheckoutResponse(
        success=True,
        message="Order placed successfully",
        order_id=order_id,
        payment_method=request.payment_method,
        payment_status=payment_status,
        transaction_id=transaction_id,
        total_amount=total_amount
    )



@app.get("/cart/interaction-check")
def interaction_check(db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    cart_items_db = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    cart_items = [{"id": str(i.medicine_id), "qty": i.quantity} for i in cart_items_db]
    return check_interactions(cart_items)


@app.get("/cart/refill-status")
def refill_status(db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    cart_items_db = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    alerts = []
    
    for item in cart_items_db:
        # We need package_size for duration calculation
        package_size = "1"
        product_name = "Unknown"
        if supabase:
            try:
                res = supabase.table("pharmacy_products").select("product_name, package_size").eq("product_id", item.medicine_id).limit(1).single().execute()
                if res.data:
                    package_size = res.data.get("package_size", "1")
                    product_name = res.data.get("product_name", "Unknown")
            except: pass
            
        units_per_pack = parse_units(package_size)
        total_units = item.quantity * units_per_pack
        days_remaining = total_units / item.dosage_per_day if item.dosage_per_day > 0 else 0
        
        if days_remaining <= 5:
            alerts.append({
                "id": str(item.medicine_id),
                "name": product_name,
                "days_remaining": round(days_remaining, 1),
                "message": "Refill soon"
            })
    return alerts




@app.get("/health/risk-index")
def health_risk_index():
    return calculate_health_risk()


@app.get("/cart")
def cart_get(db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
    
    items = []
    total = 0.0
    
    for entry in cart_items:
        # Fetch medicine details for additional info (category, rx requirement, etc)
        requires_prescription = False
        product_name = "Unknown"
        category = "Medicine"
        package_size = "1"
        
        if supabase:
            try:
                response = supabase.table("pharmacy_products").select("*").eq("product_id", entry.medicine_id).limit(1).single().execute()
                if response.data:
                    m = response.data
                    product_name = m.get("product_name", "Unknown")
                    requires_prescription = m.get("requires_prescription", False)
                    category = m.get("category", "Medicine")
                    package_size = m.get("package_size", "1")
            except:
                pass
        
        subtotal = round(entry.price * entry.quantity, 2)
        total += subtotal
        
        # Duration analysis logic
        units_per_pack = parse_units(package_size)
        total_units = entry.quantity * units_per_pack
        days_remaining = total_units / entry.dosage_per_day if entry.dosage_per_day > 0 else 0
        
        refill_date = None
        if days_remaining > 0:
            refill_date = (datetime.now() + timedelta(days=days_remaining)).strftime("%Y-%m-%d")

        items.append({
            "id":             str(entry.medicine_id),
            "name":           product_name,
            "price":          entry.price,
            "qty":            entry.quantity,
            "category":       category,
            "subtotal":       subtotal,
            "dosage_per_day": entry.dosage_per_day,
            "units_per_pack": units_per_pack,
            "days_remaining": round(days_remaining, 1),
            "predicted_refill_date": refill_date,
            "requires_prescription": requires_prescription,
            "prescription_url": entry.prescription_url
        })

    return {
        "items":      items,
        "total":      round(total, 2),
        "item_count": sum(i["qty"] for i in items),
        "prediction_summary": {
            "upcoming_refills":  len([i for i in items if i["days_remaining"] > 0 and i["days_remaining"] < 14]),
            "critical_shortage": len([i for i in items if i["days_remaining"] > 0 and i["days_remaining"] < 5])
        }
    }

# Duplicate /me removed


@app.delete("/cart/remove/{medicine_id}")
def cart_remove(medicine_id: str, qty: int = 1, remove_all: bool = False, db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    mid = int(medicine_id)
    cart_item = db.query(models.CartItem).filter(
        models.CartItem.user_id == current_user.id,
        models.CartItem.medicine_id == mid
    ).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not in cart")
    
    if remove_all or cart_item.quantity <= qty:
        db.delete(cart_item)
        db.commit()
        return {"message": "Removed from cart"}
    else:
        cart_item.quantity -= qty
        db.commit()
        return {"message": f"Quantity decreased by {qty}", "qty": cart_item.quantity}


@app.delete("/cart/clear")
def cart_clear(db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Cart cleared"}



# ── Chatbot Endpoint ─────────────────────────────────────────────────────────

# ── Agentic AI System Prompt ─────────────────────────────────────────────────

AGENT_SYSTEM_INSTRUCTION = """
You are an Intelligent Agent Router for a pharmacy system. 
You must analyze the user message and output a structured JSON tool call.

CRITICAL CAPABILITY: VOICE & TYPO TOLERANCE
Users often speak via a mic or make typos (e.g. 'perasetamos' instead of 'Paracetamol'). 
You MUST use your internal medical knowledge to interpret the user's intent even if the spelling is incorrect. 
Choose the tool parameters based on the most likely pharmaceutical match.

AVAILABLE TOOLS:
- check_stock(medicine_name: string)
- add_to_cart(user_id: string, medicine_id: string, quantity: integer)
- remove_from_cart(user_id: string, medicine_id: string)
- view_cart(user_id: string)
- create_order(user_id: string)
- process_payment(order_id: string, payment_method: string)
- track_order(order_id: string)
- cancel_order(order_id: string)
- send_email(user_id: string, subject: string, message: string)
- trigger_webhook(event_type: string, payload: object)
- refill_prediction(user_id: string)
- find_nearby_hospitals()
- general_query(message: string)
- greeting()

CRITICAL RULES:
1. You MUST ONLY return valid JSON. No markdown, no explanations.
2. The JSON MUST follow this exact format:
{
  "tool": "add_to_cart",
  "parameters": {
     "user_id": "string",
     "medicine_name": "string",
     "medicine_id": "string",
     "quantity": 2,
     "order_id": "string",
     "payment_method": "string",
     "subject": "string",
     "message": "string"
  }
}
3. If the user mentions symptoms (e.g. fever, headache), use check_stock with medicine_name as the symptom.
4. If search results (Inventory) are empty, still try to identify the medicine name from the user message and use it in the tool parameter.
"""

# ── Action Executor ──────────────────────────────────────────────────────────
def _translate_response(msg: str, lang: str) -> str:
    """Translate response message to user's language using Groq (primary) or Gemini (fallback)."""
    if lang == "en":
        return msg
        
    # 1. Try Groq (Primary - Fast & Reliable)
    try:
        if groq_client:
            # Map ISO code to name for prompt clarity
            lang_map = {"hi": "Hindi", "mr": "Marathi"}
            target_lang = lang_map.get(lang, lang)
            
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": f"You are a professional medical translator. Translate the text to {target_lang}. Return ONLY the translated text. Preserve all medicine names, prices (₹), and numbers exactly as they are."},
                    {"role": "user", "content": msg}
                ],
                max_tokens=500,
                temperature=0.1,
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"DEBUG: Groq translation failed: {e}")

    # 2. Try Gemini (Fallback)
    try:
        from app.language_processor import _get_translation_model
        model = _get_translation_model()
        if model:
            prompt = f"Translate the following medical assistant message to {lang}. Return ONLY the translated text. Preserve all numbers, prices (₹), and medicine names. Text: {msg}"
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
    except Exception as e:
        print(f"DEBUG: Gemini translation failed: {e}")

    return msg

def execute_agent_action(db: Session, intent: AgentIntent, inventory_data: list, current_user: Optional[models.User] = None, detected_language: str = "en") -> AgentResponse:

    """Backend logic to execute intent from Gemini"""
    safety_agent = get_safety_agent()
    
    # Validation step using DB
    kwargs = {}
    if intent.medicine_name: kwargs["medicine_name"] = intent.medicine_name
    if intent.medicine_id: kwargs["medicine_id"] = intent.medicine_id
    if intent.quantity: kwargs["quantity"] = intent.quantity
    if intent.intent == "place_order": kwargs["cart"] = list(_cart.values())
    
    safety_decision = safety_agent.validate_intent(db=db, intent=intent.intent, **kwargs)
    
    # If safety check fails, return the safety reason
    if not safety_decision.approved:
        response_message = safety_decision.reason
        if safety_decision.requires_prescription_upload:
            response_message += " Please upload your prescription to proceed."
        return AgentResponse(
            success=False,
            message=_translate_response(response_message, detected_language),
            data={
                "requires_prescription_upload": True,
                "medicine_name": intent.medicine_name
            },
            action="upload_prescription"
        )

    # Intent execution
    if intent.intent == "greeting":
        greetings = {
            "hi": "नमस्ते! मैं आपका फार्मेसी असिस्टेंट हूं। मैं आपकी कैसे मदद कर सकता हूं?",
            "mr": "नमस्कार! मी तुमचा फार्मसी असिस्टंट आहे. मी तुमची कशी मदत करू शकतो?",
        }
        msg = greetings.get(detected_language, "Hello! I'm your pharmacy assistant. How can I help you today?")
        return AgentResponse(
            success=True,
            message=msg,
            action_taken="greeting"
        )
    
    elif intent.intent == "general_query":
        # Check if the query mentions symptoms - try to recommend medicines
        from app.language_processor import get_medicine_search_terms
        summary = intent.user_message_summary or ""
        med_name = intent.medicine_name or ""
        search_text = f"{med_name} {summary}".strip()
        symptom_meds = get_medicine_search_terms(search_text)
        
        if symptom_meds and inventory_data:
            # We have symptom matches - find them in inventory
            found = []
            for med_term in symptom_meds[:5]:
                for item in inventory_data:
                    if med_term.lower() in item.get('name', '').lower():
                        found.append(item)
                        break
            if found:
                med_list = ", ".join([f"{m['name']} (₹{m.get('price', 0)})" for m in found[:3]])
                msg = f"For {search_text}, I recommend: {med_list}. Would you like to add any to your cart?"
                return AgentResponse(
                    success=True,
                    message=_translate_response(msg, detected_language),
                    data={"medicines": found[:3]},
                    action_taken="general_query"
                )
        
        msg = f"I understand you're asking about: {intent.user_message_summary}. How can I assist you further?"
        return AgentResponse(
            success=True,
            message=_translate_response(msg, detected_language),
            action_taken="general_query"
        )
    
    elif intent.intent == "check_stock":
        if not intent.medicine_name:
            msg = "Please specify which medicine you'd like to check."
            return AgentResponse(
                success=False,
                message=_translate_response(msg, detected_language),
                action_taken="check_stock"
            )
        
        # ── SYMPTOM-BASED SEARCH: Map symptoms to actual medicines ────
        from app.language_processor import get_medicine_search_terms
        symptom_meds = get_medicine_search_terms(intent.medicine_name)
        
        if symptom_meds:
            # This is a symptom query - find matching medicines in inventory
            found = []
            for med_term in symptom_meds[:6]:
                for item in inventory_data:
                    if med_term.lower() in item.get('name', '').lower():
                        if item not in found:
                            found.append(item)
            
            # Also search the full database if inventory_data doesn't have enough
            if len(found) < 2:
                for med_term in symptom_meds[:4]:
                    extra = search_medicines(db, search=med_term)
                    for item in extra:
                        if item not in found:
                            found.append(item)
            
            if found:
                med_list = "\n".join([f"• {m['name']} — ₹{m.get('price', 0)} ({m.get('stock_qty', 0)} in stock)" for m in found[:5]])
                msg = f"For {intent.medicine_name}, I found these medicines:\n{med_list}\n\nWould you like to add any to cart? Just say the name!"
                return AgentResponse(
                    success=True,
                    message=_translate_response(msg, detected_language),
                    data={"medicines": found[:5], "symptom": intent.medicine_name},
                    action_taken="check_stock"
                )

    elif intent.intent == "find_nearby_hospitals":
        hospitals = [
            {"name": "Sahyadri Super Speciality Hospital", "distance": "1.2 km", "contact": "+91 20 6721 5000", "address": "Plot No. 30-C, Erandwane, Pune"},
            {"name": "Noble Hospital", "distance": "2.5 km", "contact": "+91 20 6628 5000", "address": "153, Magarpatta City Rd, Hadapsar, Pune"},
            {"name": "Jehangir Hospital", "distance": "3.8 km", "contact": "+91 20 6681 1000", "address": "32, Sassoon Rd, Central Railway Colony, Pune"},
            {"name": "Columbia Asia Hospital", "distance": "4.1 km", "contact": "+91 20 7129 0129", "address": "22/2A, Mundhwa - Kharadi Rd, Pune"},
            {"name": "Ruby Hall Clinic", "distance": "5.0 km", "contact": "+91 20 6645 5100", "address": "40, Sassoon Rd, Sangamvadi, Pune"}
        ]
        
        hospital_list = "\n".join([f"🏥 **{h['name']}** - {h['distance']}\n📞 Contact: {h['contact']}\n📍 {h['address']}" for h in hospitals])
        
        msg = f"🚨 **Emergency Response Activated** 🚨\n\nI have found several nearby hospitals for you:\n\n{hospital_list}\n\n**Please call an ambulance (108/102) immediately if this is a life-threatening emergency!**"
        
        return AgentResponse(
            success=True,
            message=_translate_response(msg, detected_language),
            data={"hospitals": hospitals},
            action_taken="find_nearby_hospitals"
        )
        
        # ── DIRECT MEDICINE SEARCH ────────────────────────────────────
        # Search for medicine in inventory
        medicine = None
        for item in inventory_data:
            if intent.medicine_name.lower() in item.get('name', '').lower():
                medicine = item
                break
        
        # ── Fuzzy fallback via medicine_matcher ──────────────────────
        fuzzy_confidence = None
        if not medicine:
            try:
                from app.medicine_matcher import match_medicine_name
                match_result = match_medicine_name(intent.medicine_name, db)
                if match_result["matched_name"]:
                    fuzzy_confidence = match_result["confidence"]
                    matched = match_result["matched_name"]
                    for item in inventory_data:
                        if matched.lower() in item.get('name', '').lower():
                            medicine = item
                            break
            except Exception as e:
                logger.error(f"Fuzzy match fallback failed in check_stock: {e}")
        
        if not medicine:
            msg = f"Sorry, I couldn't find '{intent.medicine_name}' in our inventory."
            return AgentResponse(
                success=False,
                message=_translate_response(msg, detected_language),
                action_taken="check_stock"
            )
        
        # Resilient stock check: support both 'stock_qty' and 'stock_quantity' keys
        stock_qty = medicine.get('stock_qty')
        if stock_qty is None:
            stock_qty = medicine.get('stock_quantity', 0)
        
        # Build "Did you mean?" prefix when fuzzy-matched
        prefix = ""
        if fuzzy_confidence is not None and fuzzy_confidence < 100:
            prefix = f"Did you mean {medicine['name']}? (Confidence: {fuzzy_confidence:.0f}%)\n\n"
        
        if stock_qty <= 0:
            msg = f"{prefix}{medicine['name']} is currently out of stock. We'll notify you when it's available."
            return AgentResponse(
                success=False,
                message=_translate_response(msg, detected_language),
                data={"medicine": medicine, "in_stock": False},
                action_taken="check_stock"
            )
        else:
            msg = f"{prefix}{medicine['name']} is in stock! We have {stock_qty} units available at ₹{medicine.get('price', 0)} each."
            return AgentResponse(
                success=True,
                message=_translate_response(msg, detected_language),
                data={"medicine": medicine, "in_stock": True, "stock_qty": stock_qty},
                action_taken="check_stock"
            )
    
    elif intent.intent == "add_to_cart":
        if not intent.medicine_name:
            return AgentResponse(
                success=False,
                message="Please specify which medicine you'd like to add.",
                action_taken="add_to_cart"
            )
        
        # ── SYMPTOM-BASED CHECK: If they try to "add" a symptom like 'fever' ──
        from app.language_processor import get_medicine_search_terms
        symptom_meds = get_medicine_search_terms(intent.medicine_name)
        if symptom_meds and len(symptom_meds) > 1: # It's likely a symptom
            found = []
            for med_term in symptom_meds[:5]:
                for item in inventory_data:
                    if med_term.lower() in item.get('name', '').lower():
                        found.append(item)
                        break
            if found:
                med_list = ", ".join([f"{m['name']} (₹{m.get('price', 0)})" for m in found[:3]])
                msg = f"I found several medicines for '{intent.medicine_name}': {med_list}. Which one would you like to add?"
                return AgentResponse(
                    success=True,
                    message=_translate_response(msg, detected_language),
                    data={"medicines": found[:3]},
                    action_taken="general_query"
                )            
        # ═══════════════════════════════════════════════════════════════
        # SAFETY & POLICY AGENT VALIDATION
        # ═══════════════════════════════════════════════════════════════
        # This part is now handled by the initial safety_decision check at the top of the function.
        # The safety_decision.approved check already happened.
        
        medicine_data = safety_decision.medicine_data
        
        # If medicine_data is None, it means the safety agent couldn't find the medicine
        if not medicine_data:
            msg = f"Sorry, I couldn't find '{intent.medicine_name}' in our inventory."
            return AgentResponse(
                success=False,
                message=_translate_response(msg, detected_language),
                action_taken="add_to_cart"
            )
        
        # Stock check (Resilient - try both key names)
        stock_qty = medicine_data.get('stock_qty')
        if stock_qty is None:
            stock_qty = medicine_data.get('stock_quantity', 0)
        
        requested_qty = intent.quantity or 1
        if stock_qty < requested_qty:
            msg = f"Sorry, {medicine_data['name']} has only {stock_qty} units in stock. You requested {requested_qty}."
            return AgentResponse(
                success=False,
                message=_translate_response(msg, detected_language),
                action_taken="add_to_cart"
            )
        
        medicine_id = medicine_data['id']
        
        # Add to cart (Database Persistence)
        if not current_user:
            return AgentResponse(
                success=False,
                message="Please login to add items to your cart.",
                action_taken="add_to_cart"
            )

        mid = int(medicine_id)
        cart_item = db.query(models.CartItem).filter(
            models.CartItem.user_id == current_user.id,
            models.CartItem.medicine_id == mid
        ).first()

        if cart_item:
            cart_item.quantity += requested_qty
        else:
            cart_item = models.CartItem(
                user_id=current_user.id,
                medicine_id=mid,
                quantity=requested_qty,
                price=float(medicine_data.get("price") or 0)
            )
            db.add(cart_item)
        
        db.commit()
        db.refresh(cart_item)

        # Build response message with warnings if any
        response_message = f"Added {requested_qty} x {medicine_data['name']} to your cart. Total: ₹{medicine_data['price'] * requested_qty}."
        
        if safety_decision.warnings:
            response_message += "\n\n⚠️ Important notices:\n" + "\n".join(safety_decision.warnings)
        
        response_message += " Do you need anything else?"
        
        return AgentResponse(
            success=True,
            message=response_message,
            data={
                "id": str(medicine_id),
                "name": medicine_data['name'],
                "qty": cart_item.quantity,
                "warnings": safety_decision.warnings
            },
            action_taken="add_to_cart"
        )

    
    elif intent.intent == "remove_from_cart":
        if not current_user:
            return AgentResponse(success=False, message="Please login to manage your cart.", action_taken="remove_from_cart")
            
        if not intent.medicine_name and not intent.medicine_id:
            return AgentResponse(success=False, message="Please specify which item you'd like to remove from cart.", action_taken="remove_from_cart")
        
        # Find item in DB cart
        cart_item = None
        if intent.medicine_id:
            cart_item = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id, models.CartItem.medicine_id == int(intent.medicine_id)).first()
        elif intent.medicine_name:
            # Fuzzy name search in cart
            items_in_cart = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
            for item in items_in_cart:
                # Fetch name from Supabase or assuming we can match it
                res = supabase.table("pharmacy_products").select("product_name").eq("product_id", item.medicine_id).limit(1).single().execute()
                if res.data and intent.medicine_name.lower() in res.data["product_name"].lower():
                    cart_item = item
                    break
        
        if not cart_item:
            msg = f"'{intent.medicine_name or intent.medicine_id}' is not in your cart."
            return AgentResponse(success=False, message=_translate_response(msg, detected_language), action_taken="remove_from_cart")
        
        qty_to_remove = intent.quantity or 1
        if cart_item.quantity <= qty_to_remove:
            db.delete(cart_item)
            db.commit()
            msg = "Removed item from your cart."
            return AgentResponse(success=True, message=_translate_response(msg, detected_language), action_taken="remove_from_cart")
        else:
            cart_item.quantity -= qty_to_remove
            db.commit()
            msg = f"Reduced quantity. Current quantity: {cart_item.quantity}"
            return AgentResponse(success=True, message=_translate_response(msg, detected_language), action_taken="remove_from_cart")
    
    elif intent.intent == "clear_cart":
        if not current_user:
            return AgentResponse(success=False, message="Please login to manage your cart.", action_taken="clear_cart")
        db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).delete()
        db.commit()
        msg = "Your cart has been cleared."
        return AgentResponse(success=True, message=_translate_response(msg, detected_language), action_taken="clear_cart")
    
    elif intent.intent == "view_cart":
        if not current_user:
            return AgentResponse(success=False, message="Please login to view your cart.", action_taken="view_cart")
            
        cart_items_db = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
        if not cart_items_db:
            msg = "Your cart is currently empty."
            return AgentResponse(success=True, message=_translate_response(msg, detected_language), data={"cart_items": []}, action_taken="view_cart")
        
        cart_items = []
        for ci in cart_items_db:
            name = "Medicine"
            if supabase:
                try:
                    res = supabase.table("pharmacy_products").select("product_name").eq("product_id", ci.medicine_id).limit(1).single().execute()
                    if res.data: name = res.data.get("product_name", "Medicine")
                except: pass
            cart_items.append({"name": name, "price": ci.price, "qty": ci.quantity})
            
        total = sum(item['price'] * item['qty'] for item in cart_items)
        item_count = sum(item['qty'] for item in cart_items)
        
        message_lines = [f"🛒 Your Cart ({item_count} items):", ""]
        for item in cart_items:
            message_lines.append(f"• {item['name']} - {item['qty']} x ₹{item['price']} = ₹{item['price']*item['qty']:.2f}")
        message_lines.append(f"\n💰 Total: ₹{total:.2f}")
        
        return AgentResponse(
            success=True,
            message=_translate_response("\n".join(message_lines), detected_language),
            data={"cart_items": cart_items, "total": round(total, 2), "item_count": item_count},
            action_taken="view_cart"
        )
    
    elif intent.intent in ["place_order", "create_order"]:
        if not current_user:
            return AgentResponse(success=False, message="Please login to place an order.", action_taken="place_order")
            
        cart_items_db = db.query(models.CartItem).filter(models.CartItem.user_id == current_user.id).all()
        if not cart_items_db:
            return AgentResponse(success=False, message="Your cart is empty.", action_taken="place_order")
            
        total = sum(item.price * item.quantity for item in cart_items_db)
        
        if not intent.payment_method:
            msg = f"Your cart total is ₹{total:.2f}. Please say 'UPI' or 'COD' to choose a payment method."
            return AgentResponse(success=False, message=_translate_response(msg, detected_language), data={"needs_payment_method": True}, action_taken="place_order")
        
        pm_lower = intent.payment_method.lower()
        if any(keyword in pm_lower for keyword in ['upi', 'online', 'paytm', 'gpay', 'phonepe', 'scan']):
            msg = f"Please scan the QR code to complete your UPI payment of ₹{total:.2f}."
            return AgentResponse(success=True, message=_translate_response(msg, detected_language), data={"total": total, "payment_method": "UPI"}, action_taken="require_upi_scan")
        
        msg = f"I am processing your Cash on Delivery order for ₹{total:.2f} now."
        return AgentResponse(success=True, message=_translate_response(msg, detected_language), data={"total": total, "payment_method": "COD"}, action_taken="trigger_cod_checkout")

            
    elif intent.intent == "track_order":
        if not intent.order_id:
            msg = "Please provide your order ID to track your order."
            return AgentResponse(
                success=False,
                message=_translate_response(msg, detected_language),
                action_taken="track_order"
            )
        
        # Track order
        msg = f"Tracking order {intent.order_id}. Please wait..."
        return AgentResponse(
            success=True,
            message=_translate_response(msg, detected_language),
            data={"order_id": intent.order_id},
            action_taken="track_order"
        )
    
    elif intent.intent == "cancel_order":
        if not intent.order_id:
            msg = "Please provide the order ID you'd like to cancel."
            return AgentResponse(
                success=False,
                message=_translate_response(msg, detected_language),
                action_taken="cancel_order"
            )
        
        msg = f"Order {intent.order_id} cancellation initiated. Our team will process this shortly."
        return AgentResponse(
            success=True,
            message=_translate_response(msg, detected_language),
            data={"order_id": intent.order_id},
            action_taken="cancel_order"
        )
    
    elif intent.intent == "refill_prediction":
        # Get refill predictions for user
        try:
            predictor = get_refill_predictor()
            user_id = "default_user_id" # Need session mapping here
            alerts = predictor.predict_refills_for_user(db, user_id)
            print(f"DEBUG: Checking refill alerts for {user_id}, found {len(alerts)} alerts")
            
            if alerts:
                # Build message with all alerts
                alert_messages = []
                for alert in alerts:
                    alert_messages.append(alert.alert_message)
                
                combined_message = "\n\n".join(alert_messages)
                
                return AgentResponse(
                    success=True,
                    message=_translate_response(combined_message, detected_language),
                    data={
                        "alerts": [
                            {
                                "medicine": a.medicine_name,
                                "days_remaining": a.days_remaining,
                                "exhaustion_date": a.estimated_exhaustion_date.strftime('%Y-%m-%d')
                            }
                            for a in alerts
                        ]
                    },
                    action_taken="refill_prediction"
                )
            else:
                return AgentResponse(
                    success=True,
                    message="Good news! All your medicines have sufficient supply. We'll notify you when it's time to refill.",
                    action_taken="refill_prediction"
                )
        except Exception as e:
            print(f"Error in refill prediction: {e}")
            import traceback
            traceback.print_exc()
            return AgentResponse(
                success=True,
                message="I can help you track your medicine refills. Just let me know which medicine you'd like to check!",
                action_taken="refill_prediction"
            )
    
    else:
        return AgentResponse(
            success=False,
            message="I didn't understand that request. Could you please rephrase?",
            action_taken="unknown"
        )


# ── AUTH ENDPOINTS ───────────────────────────────────────────────────────────
@app.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = auth.get_password_hash(user.password)
        db_user = models.User(
            name=user.name,
            email=user.email,
            phone=user.phone,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        import traceback
        print(f"ERROR in /register: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": user
    }

@app.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.patch("/me", response_model=schemas.UserResponse)
def update_user_profile(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db)
):
    """Update current user's profile"""
    # Update only provided fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user


# ── Deterministic Intent Parser ──────────────────────────────────────────────
def extract_intent_regex(message: str) -> Optional[AgentIntent]:
    """
    Fallback deterministic parser for common patterns to bypass AI flaky-ness.
    Handles: add to cart, check stock, remove from cart, clear cart.
    """
    msg = message.lower().strip()
    
    # 1. ADD TO CART: "add 5 paracetamol 500mg", "add crocin to cart"
    # Matches patterns like: "add [qty] [medicine] [optional noise]"
    add_match = re.search(r'\badd\b\s*(?:(\d+)\s+)?(.*?)(?:\s+to\s+cart|\s+to\s+my\s+cart|$)', msg)
    if add_match and len(add_match.group(2).strip()) > 2:
        qty_str = add_match.group(1)
        qty = int(qty_str) if qty_str else 1
        med_name = add_match.group(2).strip()
        # Clean med_name of noise
        return AgentIntent(
            intent="add_to_cart",
            medicine_name=med_name.title(),
            quantity=qty,
            requires_prescription_check=True, # Safety agent will verify actual RX status
            user_message_summary=f"Regex: Add {qty} {med_name}"
        )

    # 2. CHECK STOCK: "is paracetamol available?", "check stock for crocin"
    check_match = re.search(r'\b(?:check|is|do you have|available|stock)\b\s*(.*?)\s*(?:\bavailable\b|\bstock\b|\bin stock\b|\bavailable\b|$)', msg)
    if check_match and len(check_match.group(1).strip()) > 2:
        med_name = check_match.group(1).strip()
        med_name = re.sub(r'^(?:is|check|for|has|got)\s+', '', med_name)
        return AgentIntent(
            intent="check_stock",
            medicine_name=med_name.title(),
            quantity=1,
            user_message_summary=f"Regex: Check stock for {med_name}"
        )

    # 3. CLEAR/VIEW CART
    if any(p in msg for p in ["clear cart", "empty cart", "clear my cart"]):
        return AgentIntent(intent="clear_cart", user_message_summary="Regex: Clear cart")
    if any(p in msg for p in ["view cart", "show cart", "what's in my cart"]):
        return AgentIntent(intent="view_cart", user_message_summary="Regex: View cart")

    # 4. PLACE ORDER
    if any(p in msg for p in ["place order", "checkout", "buy now", "confirm order", "place my order"]):
        return AgentIntent(intent="place_order", user_message_summary="Regex: Place order")
        
    # 5. PAYMENT METHOD SELECTION
    if any(p in msg for p in ["upi", "online", "paytm", "gpay", "phonepe", "scan"]):
        return AgentIntent(intent="place_order", payment_method="UPI", user_message_summary="Regex: Select UPI payment")
    if any(p in msg for p in ["cod", "cash"]):
        return AgentIntent(intent="place_order", payment_method="Cash on Delivery", user_message_summary="Regex: Select COD payment")

    return None


@app.post("/chat")
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db), current_user: Optional[models.User] = Depends(auth.get_current_user_optional)):
    """
    Agentic AI Chat Endpoint with Full Observability
    Step 1: Gemini analyzes user message and returns structured intent JSON
    Step 2: Backend executes the action based on intent
    Step 3: Return final response to user
    """
    try:
        safe_msg = request.message[:50].encode('ascii', 'replace').decode('ascii')
        print(f"DEBUG: Received chat request: {safe_msg}")
        start_time = time.time()
        raw_user_message = request.message

        # ── Language Detection & Translation ────────────────────────────
        lang_result = process_user_input(raw_user_message)
        user_message = lang_result["translated_text"]  # English text for intent extraction
        detected_language = lang_result["detected_language"]
        original_text = lang_result.get("original_text", raw_user_message)

        # ── Deterministic Greeting Check ────────────────────────────────
        # Avoid hitting AI for simple greetings
        greeting_words = {"hi", "hello", "hey", "namaste", "hola", "greetings", "good morning", "good evening", "good afternoon"}
        if user_message.lower().strip().rstrip('!') in greeting_words:
            print(f"DEBUG: Quick greeting matched: {user_message}")
            greeting_intent = AgentIntent(intent="greeting", user_message_summary="User greeting")
            action_result = execute_agent_action(db, greeting_intent, [], current_user, detected_language)

            return {
                "success": True,
                "message": action_result.message,
                "data": {},
                "action_taken": "greeting",
                "intent": "greeting",
                "detected_language": detected_language,
                "original_text": original_text,
            }

        if detected_language != "en":
            safe_en = user_message[:80].encode('ascii', 'replace').decode('ascii')
            print(f"DEBUG: Translated [{detected_language}] → EN: {safe_en}")
    except Exception as e:
        print(f"ERROR at start of chat_endpoint: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"Error: {str(e)}"}
    
    # 1. Context Gathering - Search relevant medicines
    matching_medicines = []
    
    if user_message and len(user_message) > 2:
        categories = ["Medicine", "Skincare", "Body Care", "Sanitary", "Supplement"]
        detected_cat = None
        for cat in categories:
            if cat.lower() in user_message.lower():
                detected_cat = cat
                break
        
        # Clean query for search
        strip_words = ["show", "me", "i", "want", "to", "order", "purchase", "find", "search", "please", "tablets", "units", "need", "give", "tablet", "medicine", "available", "price", "is", "it", "the", "for", "get", "have", "some", "any", "what", "how", "much", "cost"]
        clean_query = user_message.lower()
        for sw in strip_words:
            clean_query = re.sub(rf'\b{sw}\b', '', clean_query)
        clean_query = clean_query.strip()
        
        try:
            if detected_cat:
                results = search_medicines(db, category=detected_cat)
                matching_medicines = results[:10] 
            else:
                results = search_medicines(db, search=clean_query)
                if not results and len(clean_query.split()) > 1:
                    words = sorted(clean_query.split(), key=len, reverse=True)
                    for w in words[:1]:
                        results = search_medicines(db, search=w)
                        if results: break
                
                # 1.5 Fuzzy Match Check (Denoising Pass for Voice/STT Typos)
                if not results and clean_query and len(clean_query) >= 3:
                    try:
                        # Fetch medicine names to check for close matches
                        all_p_res = supabase.table("pharmacy_products").select("product_name").limit(300).execute()
                        all_names = [p["product_name"] for p in all_p_res.data]
                        close_matches = difflib.get_close_matches(clean_query, all_names, n=2, cutoff=0.4)
                        if close_matches:
                            print(f"DEBUG: Fuzzy match detected typos - suggesting: {close_matches}")
                            for f_name in close_matches:
                                fuzzy_results = search_medicines(db, search=f_name)
                                if fuzzy_results:
                                    results.extend(fuzzy_results)
                    except Exception as fe:
                        print(f"DEBUG: Fuzzy matching error: {fe}")
                
                matching_medicines = results[:5]
        except: 
            pass

    def json_serializable(obj):
        """Helper to serialize complex types like datetimes and SQLAlchemy models."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return str(obj)

    try:
        inv_data = matching_medicines
        inventory_json = json.dumps(inv_data, default=json_serializable)
        cart_json = json.dumps(list(_cart.values()), default=json_serializable)
        
        # Fetch 5 most recent orders from database
        recent_orders_db = db.query(models.Order).order_by(models.Order.created_at.desc()).limit(5).all()
        recent_orders = []
        for o in recent_orders_db:
            recent_orders.append({
                "order_id": o.order_id,
                "total_amount": o.total_amount,
                "shipping_status": o.shipping_status,
                "created_at": o.created_at.isoformat() if o.created_at else None
            })
        orders_json = json.dumps(recent_orders, default=json_serializable)
    except Exception as e:
        print(f"DEBUG: Data serialization error: {e}")
        inventory_json, cart_json, orders_json = "[]", "[]", "[]"

    # 2. Build prompt for OpenAI Agent
    prompt = f"{AGENT_SYSTEM_INSTRUCTION}\n\nInventory: {inventory_json}\nCart: {cart_json}\nRecent Orders: {orders_json}\n\nUser Language: {detected_language}\nUser Message: {user_message}\n\nReturn ONLY valid JSON with intent and entities."

    # 3. Get Intent from OpenAI (Replaces Gemini - No Action Execution)
    intent_data = None
    last_error = "OpenAI API call failed"

    # ── Deterministic Fallbacks (Bypasses AI if pattern matches) ─────────────
    # This ensures "Add 5 Torrent Paracetamol" works even if OpenAI is down!
    intent_data = extract_intent_regex(user_message)

    # DEMO FALLBACK: Specific check for montelukast
    if not intent_data and "montelukast" in user_message.lower():
        print("DEBUG: Using legacy deterministic fallback for Montelukast")
        intent_data = AgentIntent(
            intent="add_to_cart",
            medicine_name="Mankind Montelukast 10mg",
            quantity=1,
            requires_prescription_check=True,
            user_message_summary="User wants to add Mankind Montelukast (Demo Fallback)"
        )

    # Check if Groq is configured
    if not groq_api_key or not groq_client:
        print("ERROR: No GROQ_API_KEY found!")
        return {"success": False, "message": "AI Assistant Error: Groq API key not configured. Please check backend/.env file."}

    if not intent_data:
        print("DEBUG: Attempting Groq llama-3.3-70b-versatile...")
        try:
            m_start = time.time()
            # ── Groq API Call (replaces OpenAI/Gemini) ──
            # Format history for LLM
            history_str = ""
            if request.history:
                history_str = "\nConversation History:\n" + "\n".join([f"{h.get('role', 'user')}: {h.get('content', '')}" for h in request.history[-6:]]) # Last 3 turns (6 messages)

            user_name = current_user.name if current_user else "Guest"
            prompt = f"{AGENT_SYSTEM_INSTRUCTION}\n\nUser Name: {user_name}\nInventory: {inventory_json}\nCart: {cart_json}\nRecent Orders: {orders_json}\n{history_str}\n\nUser Language: {detected_language}\nUser Message: {user_message}\n\nReturn ONLY valid JSON with tool and parameters."
            
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": AGENT_SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1,
            )
            print("DEBUG: Groq response received")

            response_text = response.choices[0].message.content.strip() if response.choices else ""

            if not response_text:
                print("DEBUG: Groq returned empty response")
            else:
                print(f"DEBUG: Response length: {len(response_text)}")

                # Extract JSON from response (handle markdown code blocks)
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    parts = response_text.split('```')
                    if len(parts) >= 2:
                        response_text = parts[1].strip()

                # Find JSON object - use greedy match to get complete JSON
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if not json_match:
                    print(f"DEBUG: No JSON found in response.")
                else:
                    try:
                        intent_json = json.loads(json_match.group())
                        
                        # Validate and create structured tool call
                        tool_name = intent_json.get("tool", "general_query")
                        params = intent_json.get("parameters", {})
                        print(f"DEBUG: Parsed Tool Call -> {tool_name}, Params: {params}")
                        
                        # Map tool names to backend intent names
                        mapped_intent = tool_name
                        if tool_name == "create_order": mapped_intent = "place_order"
                        if tool_name == "process_payment": mapped_intent = "place_order"
                        
                        # Map to existing AgentIntent struct
                        intent_data = AgentIntent(
                            intent=mapped_intent,
                            medicine_name=params.get("medicine_name"),
                            medicine_id=params.get("medicine_id"),
                            quantity=params.get("quantity", 1),
                            order_id=params.get("order_id"),
                            payment_method=params.get("payment_method"),
                            user_message_summary=params.get("message", user_message[:100]),
                            requires_prescription_check=True
                        )
                        print(f"DEBUG: Tool mapped to backend in {time.time() - m_start:.2f}s")
                    except Exception as e:
                        print(f"DEBUG: JSON/Validation error: {e}")
                        intent_data = AgentIntent(
                            intent="general_query",
                            user_message_summary=user_message[:100]
                        )

        except Exception as e:
            last_error = str(e)
            print(f"DEBUG: Groq error: {last_error}")

    # 4. Handle Gemini Failure
    if not intent_data:
        friendly_error = "The AI Assistant is currently receiving high traffic. Please try again in a moment."
        if "429" in last_error or "quota" in last_error.lower():
            return {"success": False, "message": friendly_error}
        return {"success": False, "message": f"AI Assistant Error: {last_error}"}

    # 5. Execute Structured Tool Call
    try:
        # Deterministically execute the tool call business logic
        action_result = execute_agent_action(db, intent_data, matching_medicines, current_user, detected_language)

        
        # 6. Generate Natural Language Explanation based on the Tool Result
        try:
            lang_map = {"hi": "Hindi", "mr": "Marathi", "en": "English"}
            target_lang = lang_map.get(detected_language, detected_language)
            explanation_prompt = f"The user asked: '{original_text}'. The system executed the backend tool '{intent_data.intent}' with outcome: success={action_result.success}, data={json.dumps(action_result.data, default=str)}. Explain this to the user in {target_lang}. Be helpful and conversational. Do not expose internal JSON."
            explanation_response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "You are a professional pharmacy agent explaining the result of a backend software action to a patient. Output ONLY the response message."},
                          {"role": "user", "content": explanation_prompt}],
                temperature=0.2
            )
            # Override original hardcoded text with AI generated text
            action_result.message = explanation_response.choices[0].message.content.strip()
            print("DEBUG: Generated natural language explanation successfully")
        except Exception as groq_err:
            print(f"DEBUG: Failed to generate natural language explanation: {groq_err}")
            # Fallback to hardcoded message

        total_time = time.time() - start_time
        print(f"DEBUG: Total request time: {total_time:.2f}s")
        
        # Return structured response
        response = {
            "success": action_result.success,
            "message": action_result.message,
            "data": action_result.data,
            "action_taken": intent_data.intent, # Return the exact tool name
            "action": action_result.action, # Passthrough for frontend detection mapping
            "tool_executed": intent_data.intent,
            "detected_language": detected_language,
            "original_text": original_text,
        }
        
        # Add Langfuse info if enabled
        if LANGFUSE_ENABLED:
            response["langfuse_enabled"] = True
            response["langfuse_host"] = langfuse_host
        
        # Return structured response
        return response
    
    except Exception as e:
        print(f"ERROR: Action execution failed: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to process your request: {str(e)}",
            "action_taken": "error"
        }

@app.post("/scan_prescription")
async def scan_prescription(file: UploadFile = File(...)):
    """
    AI-powered prescription scanner - extracts medicine names with confidence scores
    """
    try:
        from app.vision_scanner import get_vision_scanner
        
        content = await file.read()
        scanner = get_vision_scanner()
        result = scanner.extract_medicines_from_image(content)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Prescription scan failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "medicines": [],
            "raw_text": "",
            "method": "error"
        }


@app.post("/upload_prescription")
async def upload_prescription(
    medicine_name: Optional[str] = Query(None),
    file: UploadFile = File(...)
):
    """
    Handle prescription uploads with deterministic rule-based validation.
    """
    content = await file.read()
    
    # ── OCR Extraction ────────────────────────────────────────────────────────
    ocr_text = ""
    try:
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(content))
        
        # Primary: Pytesseract
        try:
            import pytesseract
            # Common Windows Tesseract paths - try to find it if not in PATH
            tess_paths = [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Users\\' + os.getlogin() + r'\AppData\Local\Tesseract-OCR\tesseract.exe'
            ]
            for p in tess_paths:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break
                    
            ocr_text = pytesseract.image_to_string(image)
            print("✅ OCR: Pytesseract successful")
        except Exception as e:
            print(f"⚠️ Pytesseract failed: {e}. Falling back to EasyOCR.")
            # Fallback: EasyOCR
            try:
                import easyocr
                import numpy as np
                reader = easyocr.Reader(['en'])
                results = reader.readtext(np.array(image))
                ocr_text = " ".join([res[1] for res in results])
                print("✅ OCR: EasyOCR successful")
            except Exception as e2:
                print(f"❌ OCR Extraction failed: {e2}")
                # Last resort: mock text if it's a known test image or return error
                ocr_text = ""

    except Exception as e:
        print(f"❌ Image processing failed: {e}")
        return {
            "valid": False,
            "message": f"Error processing image: {str(e)}",
            "validation_result": {"valid": False, "confidence": 0, "reason": "Image processing error"},
            "extracted_text": ""
        }

    # ── Rule-Based Validation ────────────────────────────────────────────────
    print(f"DEBUG: upload_prescription called with medicine_name='{medicine_name}'")
    validator = PrescriptionValidationAgent()
    validation_result = validator.validate(ocr_text, medicine_name)
    
    # Store validation result if successful
    if validation_result["valid"] and medicine_name:
        _validated_prescriptions.add(medicine_name.lower().strip())
        print(f"✅ Prescription approved for: {medicine_name}")
    
    return {
        "valid": validation_result["valid"],
        "message": validation_result["reason"] if not validation_result["valid"] else "Prescription validated successfully.",
        "validation_result": validation_result,
        "extracted_text": ocr_text
    }

# ── Serve Frontend Static Files ─────────────────────────────────────────────
# This must be LAST so it doesn't shadow API routes.
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/site", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    print(f"OK: Frontend mounted at /site from {FRONTEND_DIR}")

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/site/index.html")
else:
    print(f"WARNING: Frontend directory not found: {FRONTEND_DIR}")
