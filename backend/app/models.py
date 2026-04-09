from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    address = Column(String, nullable=True)
    blood_group = Column(String, nullable=True)
    allergies = Column(String, nullable=True)
    chronic_conditions = Column(String, nullable=True)
    current_medications = Column(String, nullable=True)
    primary_doctor = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="customer")
    created_at = Column(DateTime, default=datetime.utcnow)

class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False)
    generic_name = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    dosage = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    stock_quantity = Column(Integer, default=0)
    minimum_stock_alert = Column(Integer, default=10)
    expiry_date = Column(String, nullable=True)
    batch_number = Column(String, nullable=True)
    requires_prescription = Column(Boolean, default=False)
    drug_interactions = Column(String, nullable=True)
    pzn = Column(String, nullable=True)
    package_size = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    total_amount = Column(Float, nullable=False)
    payment_status = Column(String, default="pending")
    order_status = Column(String, default="processing")
    prescription_url = Column(String, nullable=True)  # URL to uploaded prescription image
    prescription_required = Column(Boolean, default=False)  # Flag if order needs prescription
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.id"))
    medicine_id = Column(Integer, ForeignKey("medicines.id"))
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.id"))
    payment_method = Column(String)
    transaction_id = Column(String, nullable=True)
    payment_status = Column(String)
    paid_at = Column(DateTime, nullable=True)

class RefillAlert(Base):
    __tablename__ = "refill_alerts"

    id = Column(String, primary_key=True, index=True, default=lambda: f"ALT_{uuid.uuid4().hex[:8]}")
    user_id = Column(String, ForeignKey("users.id"))
    medicine_name = Column(String, nullable=False)
    days_remaining = Column(Integer)
    exhaustion_date = Column(DateTime)
    alert_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending") # pending, sent, acknowledged, refilled
    priority = Column(String) # high, medium, low
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class DeliveryExtension(Base):
    __tablename__ = "delivery_extensions"

    order_id = Column(String, ForeignKey("orders.id"), primary_key=True)
    delivery_status = Column(String, default="PENDING")
    assigned_agent_id = Column(String, nullable=True)
    packed_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    out_for_delivery_at = Column(DateTime, nullable=True)
    delivery_tomorrow_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"))
    medicine_id = Column(Integer, ForeignKey("medicines.id"))
    quantity = Column(Integer, default=1)
    price = Column(Float)
    dosage_per_day = Column(Integer, default=1)
    prescription_url = Column(String, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    
    # Relationships
    user = relationship("User")
    medicine = relationship("Medicine")

