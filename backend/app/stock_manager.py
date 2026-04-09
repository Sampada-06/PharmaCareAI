from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os
from datetime import datetime
from app.supabase_client import supabase

# Langfuse observe decorator (optional - for tracing)
try:
    from langfuse.decorators import observe
except ImportError:
    # Fallback if decorators not available
    def observe(name=None, **kwargs):
        def decorator(func):
            return func
        return decorator

class StockUpdate(BaseModel):
    """Stock update record"""
    medicine_id: int
    medicine_name: str
    quantity_deducted: int
    previous_stock: int
    new_stock: int
    order_id: str
    timestamp: datetime

class StockUpdateResult(BaseModel):
    """Result of stock update operation"""
    success: bool
    updates: List[StockUpdate]
    errors: List[str]
    insufficient_stock: List[Dict[str, Any]]

class StockManager:
    """
    Manages inventory stock levels using Supabase
    """
    
    def __init__(self):
        print(f"OK: Stock Manager initialized for Supabase integration")
    
    def reload_inventory(self):
        """No-op for Supabase integration (data is always fresh)"""
        pass
    
    def check_stock_availability(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check if all items have sufficient stock using Supabase
        """
        items_status = []
        insufficient_items = []
        
        if not supabase:
            return {"all_available": False, "items_status": [], "insufficient_items": [], "error": "Supabase not initialized"}

        for item in items:
            medicine_id = item.get('id')
            requested_qty = item.get('qty', 0)
            
            # Handle potential string ID from frontend
            try:
                med_id_int = int(medicine_id)
            except (ValueError, TypeError):
                med_id_int = 0

            # Find product in inventory
            response = supabase.table("pharmacy_products").select("*").eq("product_id", med_id_int).limit(1).single().execute()
            product = response.data
            
            if not product:
                insufficient_items.append({
                    "id": medicine_id,
                    "name": item.get('name', 'Unknown'),
                    "requested": requested_qty,
                    "available": 0,
                    "reason": "Product not found"
                })
                items_status.append({
                    "id": medicine_id,
                    "available": False,
                    "reason": "Not found"
                })
            else:
                current_stock = product.get("stock_quantity", 0)
                
                if current_stock >= requested_qty:
                    items_status.append({
                        "id": medicine_id,
                        "available": True,
                        "current_stock": current_stock,
                        "requested": requested_qty
                    })
                else:
                    insufficient_items.append({
                        "id": medicine_id,
                        "name": product.get("product_name"),
                        "requested": requested_qty,
                        "available": current_stock,
                        "reason": f"Insufficient stock (need {requested_qty}, have {current_stock})"
                    })
                    items_status.append({
                        "id": medicine_id,
                        "available": False,
                        "reason": "Insufficient stock"
                    })
        
        return {
            "all_available": len(insufficient_items) == 0,
            "items_status": items_status,
            "insufficient_items": insufficient_items
        }
    
    def deduct_stock(
        self, 
        items: List[Dict[str, Any]], 
        order_id: str
    ) -> StockUpdateResult:
        """
        Permanently deduct stock for order items using Supabase updates
        """
        print(f"\n DEDUCTING SUPABASE STOCK FOR ORDER: {order_id}")
        print("-" * 70)
        
        updates = []
        errors = []
        insufficient_stock = []
        
        if not supabase:
            return StockUpdateResult(success=False, updates=[], errors=["Supabase not initialized"], insufficient_stock=[])

        try:
            for item in items:
                medicine_id = item.get('id')
                requested_qty = item.get('qty', 0)
                medicine_name = item.get('name', 'Unknown')
                
                try:
                    med_id_int = int(medicine_id)
                except (ValueError, TypeError):
                    errors.append(f"Invalid medicine ID: {medicine_id}")
                    continue

                # Find product and lock (Supabase doesn't have SELECT FOR UPDATE in REST API easily, 
                # but we can use an RPC or just update with a condition in SQL if we were using raw SQL.
                # For now, we'll do a read-then-update or preferably an update with increment logic if possible.
                # Since Supabase JS/Python client doesn't support increment directly in update() with filter,
                # we'll use the read-modify-write pattern for now, acknowledging the race condition risk.)
                
                response = supabase.table("pharmacy_products").select("stock_quantity, product_name").eq("product_id", med_id_int).limit(1).single().execute()
                product = response.data
                
                if not product:
                    errors.append(f"Product {medicine_id} not found")
                    continue
                
                previous_stock = product.get("stock_quantity", 0)
                new_stock = previous_stock - requested_qty
                
                if new_stock < 0:
                    errors.append(f"Insufficient stock for {medicine_name}")
                    insufficient_stock.append({
                        "id": medicine_id,
                        "name": medicine_name,
                        "requested": requested_qty,
                        "available": previous_stock
                    })
                    continue
                
                # Update stock
                supabase.table("pharmacy_products").update({"stock_quantity": new_stock}).eq("product_id", med_id_int).execute()
                
                # Record update
                update = StockUpdate(
                    medicine_id=med_id_int,
                    medicine_name=medicine_name,
                    quantity_deducted=requested_qty,
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    order_id=order_id,
                    timestamp=datetime.now()
                )
                updates.append(update)
                
                print(f"   OK: {medicine_name}: {previous_stock} -> {new_stock} (-{requested_qty})")
            
            success = len(errors) == 0
                
        except Exception as e:
            error_msg = f"Supabase error during stock deduction: {str(e)}"
            errors.append(error_msg)
            print(f"   ERROR: {error_msg}")
            success = False
        
        print(f"\n   Summary: {len(updates)} items updated, {len(errors)} errors")
        print("-" * 70)
        
        return StockUpdateResult(
            success=success,
            updates=updates,
            errors=errors,
            insufficient_stock=insufficient_stock
        )
    
    def get_stock_level(self, medicine_id: str) -> Optional[int]:
        """Get current stock level for a medicine via Supabase"""
        if not supabase: return None
        try:
            try:
                med_id_int = int(medicine_id)
            except (ValueError, TypeError):
                return None
                
            response = supabase.table("pharmacy_products").select("stock_quantity").eq("product_id", med_id_int).limit(1).single().execute()
            if not response.data:
                return None
            return response.data.get("stock_quantity")
        except:
            return None
    
    def get_low_stock_items(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """Get items with stock below threshold via Supabase"""
        if not supabase: return []
        try:
            response = supabase.table("pharmacy_products").select("*").lt("stock_quantity", threshold).execute()
            return [
                {
                    'id': str(m["product_id"]),
                    'product_id': str(m["product_id"]),
                    'name': m["product_name"],
                    'product_name': m["product_name"],
                    'stock_quantity': m["stock_quantity"]
                } for m in response.data
            ]
        except:
            return []

# Singleton instance
_stock_manager = None

def get_stock_manager(products_csv_path: str = None) -> StockManager:
    """Get or create stock manager instance"""
    global _stock_manager
    if _stock_manager is None:
        _stock_manager = StockManager()
    return _stock_manager
