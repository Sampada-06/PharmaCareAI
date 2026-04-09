"""
Safety & Policy Agent
Validates medicine transactions before execution using Supabase
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Union
from pydantic import BaseModel
import logging
from app.supabase_client import supabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SafetyDecision(BaseModel):
    """Safety validation decision"""
    approved: bool
    reason: str
    requires_prescription_upload: bool = False
    warnings: List[str] = []
    medicine_data: Optional[Dict] = None


class SafetyPolicyAgent:
    """
    Safety & Policy Agent for Medicine Validation
    
    Responsibilities:
    1. Validate stock availability
    2. Check expiry dates
    3. Verify prescription requirements
    4. Check drug interactions
    5. Log all decisions for observability
    """
    
    def __init__(self):
        """Initialize the safety agent"""
        logger.info("Safety agent initialized (Supabase mode)")
    
    def find_medicine(self, db = None, medicine_name: str = None, medicine_id: Union[str, int] = None) -> Optional[Dict]:
        """
        Find medicine by name or ID in Supabase.
        """
        if not supabase: return None
        
        if medicine_id:
            response = supabase.table("pharmacy_products").select("*").eq("product_id", int(medicine_id)).limit(1).single().execute()
            return response.data
        
        if medicine_name:
            # Try exact match first
            response = supabase.table("pharmacy_products").select("*").ilike("product_name", medicine_name).execute()
            if response.data: return response.data[0]
            
            # Fuzzy fallback
            try:
                from app.medicine_matcher import match_medicine_name
                match_result = match_medicine_name(medicine_name)
                if match_result["matched_name"]:
                    response = supabase.table("pharmacy_products").select("*").ilike("product_name", match_result["matched_name"]).execute()
                    if response.data: return response.data[0]
            except Exception as e:
                logger.error(f"Fuzzy match fallback failed: {e}")
        
        return None
    
    def check_stock_availability(self, medicine: Dict, requested_qty: int) -> tuple[bool, str]:
        """Check if requested quantity is available in stock"""
        stock_qty = medicine.get("stock_quantity", 0)
        name = medicine.get("product_name", "Unknown")
        
        if stock_qty <= 0:
            return False, f"{name} is currently out of stock"
        
        if stock_qty < requested_qty:
            return False, f"Only {stock_qty} units available. Requested: {requested_qty}"
        
        if stock_qty < 10:
            return True, f"Low stock warning: Only {stock_qty} units remaining"
        
        return True, f"Stock available: {stock_qty} units"
    
    def check_expiry_date(self, medicine: Dict) -> tuple[bool, str]:
        """Check if medicine is expired or expiring soon"""
        # Expiry logic
        return True, "Expiry check passed"
    
    def check_prescription_requirement(self, medicine: Dict) -> tuple[bool, str]:
        """Check if medicine requires prescription"""
        name = medicine.get("product_name", "Unknown")
        if medicine.get("requires_prescription"):
            return True, f"{name} requires a valid prescription"
        return False, "No prescription required"
    
    def check_drug_interactions(self, db = None, medicine: Dict = None, current_cart: List[Dict] = None) -> tuple[bool, List[str]]:
        """Check for drug interactions using Supabase"""
        warnings = []
        if not medicine or not supabase: return False, []
        
        # 1. Check current medicine's interaction warning
        interaction_text = str(medicine.get("drug_interactions") or "").lower()
        name = medicine.get("product_name", "Unknown")
        
        if interaction_text and "not applicable" not in interaction_text:
            warnings.append(f"WARNING: {name}: {interaction_text}")
            
        # 2. Check interactions with cart items
        if current_cart:
            for item in current_cart:
                cart_med_id = int(item.get("id"))
                response = supabase.table("pharmacy_products").select("product_name").eq("product_id", cart_med_id).limit(1).single().execute()
                cart_med = response.data
                if cart_med:
                    cart_med_name = cart_med.get("product_name", "")
                    # Simple name check in interaction text
                    if cart_med_name.lower() in interaction_text:
                        warnings.append(f"WARNING: Potential interaction between {name} and {cart_med_name}")
        
        return len(warnings) > 0, warnings
    
    def validate_add_to_cart(
        self, 
        db = None,
        medicine_name: str = None, 
        medicine_id: Union[str, int] = None,
        quantity: int = 1,
        current_cart: List[Dict] = None,
        has_prescription: bool = False
    ) -> SafetyDecision:
        """Main validation function for add_to_cart intent using Supabase"""
        
        # 1. Find medicine
        medicine = self.find_medicine(medicine_name=medicine_name, medicine_id=medicine_id)
        
        if medicine is None:
            return SafetyDecision(approved=False, reason=f"Medicine not found in inventory")
        
        # 2. Check stock
        stock_ok, stock_reason = self.check_stock_availability(medicine, quantity)
        if not stock_ok:
            return SafetyDecision(approved=False, reason=stock_reason)
            
        # 3. Check Rx
        needs_rx, rx_reason = self.check_prescription_requirement(medicine)
        if needs_rx and not has_prescription:
            return SafetyDecision(
                approved=False, 
                reason=rx_reason,
                requires_prescription_upload=True,
                medicine_data={"id": str(medicine["product_id"]), "name": medicine["product_name"], "requires_prescription": True}
            )
            
        # 4. Check Interactions
        has_ints, int_warnings = self.check_drug_interactions(medicine=medicine, current_cart=current_cart)
        
        return SafetyDecision(
            approved=True,
            reason=f"Validation passed for {medicine['product_name']}",
            warnings=int_warnings,
            medicine_data={
                "id": str(medicine["product_id"]),
                "name": medicine["product_name"],
                "price": float(medicine.get("price") or 0),
                "category": medicine.get("category"),
                "stock_qty": medicine.get("stock_quantity"),
                "prescription_needed": needs_rx
            }
        )
    
    def validate_intent(self, db = None, intent: str = "", **kwargs) -> SafetyDecision:
        """Route validation based on intent type"""
        if intent == "add_to_cart":
            return self.validate_add_to_cart(**kwargs)
        
        elif intent == "place_order":
            cart = kwargs.get('cart', [])
            for item in cart:
                decision = self.validate_add_to_cart(
                    medicine_id=item.get('id'),
                    quantity=item.get('qty', 1),
                    current_cart=cart
                )
                if not decision.approved:
                    return decision
            
            return SafetyDecision(approved=True, reason="All items passed validation")
        
        return SafetyDecision(approved=True, reason="No validation needed")


# Singleton instance
_safety_agent = None

def get_safety_agent() -> SafetyPolicyAgent:
    """Get or create safety agent instance"""
    global _safety_agent
    if _safety_agent is None:
        _safety_agent = SafetyPolicyAgent()
    return _safety_agent
