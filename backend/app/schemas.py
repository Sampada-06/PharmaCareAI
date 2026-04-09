from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Literal

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    role: str
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    primary_doctor: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    primary_doctor: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

class CheckoutRequest(BaseModel):
    payment_method: Literal["UPI", "COD"]
    user_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    prescriptions: Optional[dict] = {}  # {medicine_id: prescription_base64_data}

class CheckoutResponse(BaseModel):
    success: bool
    message: str
    order_id: str
    payment_method: str
    payment_status: str
    transaction_id: Optional[str] = None
    total_amount: float

class AgentAssignRequest(BaseModel):
    agent_id: str

class DeliveryStatusUpdate(BaseModel):
    delivery_status: str
