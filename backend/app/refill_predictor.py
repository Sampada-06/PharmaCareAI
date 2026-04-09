"""
Predictive Refill Intelligence Agent
Analyzes order history and predicts when users need medicine refills
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel
from app import models
from sqlalchemy.orm import Session
from app.database import SessionLocal

class RefillPrediction(BaseModel):
    """Model for refill prediction data"""
    user_id: str
    medicine_name: str
    last_purchase_date: datetime
    quantity_purchased: int
    dosage_frequency: str
    daily_consumption: float
    estimated_exhaustion_date: datetime
    days_remaining: int
    alert_triggered: bool
    alert_message: str
    confidence_score: float

class RefillPredictorAgent:
    """Agent that predicts medicine refill needs using database records"""
    
    def __init__(self):
        pass
    
    def parse_dosage_frequency(self, dosage_str: str) -> float:
        """Convert dosage frequency string to daily consumption rate."""
        if not dosage_str:
            return 1.0
        dosage_lower = str(dosage_str).lower()
        
        if "once daily" in dosage_lower or "1 mal" in dosage_lower:
            return 1.0
        elif "twice daily" in dosage_lower or "2 mal" in dosage_lower:
            return 2.0
        elif "three times" in dosage_lower or "3 mal" in dosage_lower:
            return 3.0
        elif "every 12 hours" in dosage_lower:
            return 2.0
        elif "every 8 hours" in dosage_lower:
            return 3.0
        elif "weekly" in dosage_lower:
            return 1.0 / 7.0
        elif "as needed" in dosage_lower:
            return 0.5
        return 1.0
    
    def predict_refills_for_user(self, db: Session, user_id: str) -> List[RefillPrediction]:
        """Predict refill needs for a specific user from DB history."""
        # Get all orders for this user
        orders = db.query(models.Order).filter(models.Order.user_id == user_id).all()
        
        predictions = []
        today = datetime.now()
        
        for order in orders:
            for item in order.items:
                try:
                    medicine = db.query(models.Medicine).get(item.medicine_id)
                    if not medicine: continue
                    if not medicine.requires_prescription: continue
                    
                    purchase_date = order.created_at
                    quantity = item.quantity
                    dosage_frequency = medicine.dosage or "Once daily"
                    
                    daily_consumption = self.parse_dosage_frequency(dosage_frequency)
                    
                    # Calculate exhaustion
                    days_supply = quantity / daily_consumption
                    exhaustion_date = purchase_date + timedelta(days=days_supply)
                    days_remaining = (exhaustion_date - today).days
                    
                    # Confidence score
                    score = 0.5 # Baseline
                    if 1 <= quantity <= 100: score += 0.2
                    if (today - purchase_date).days <= 30: score += 0.3
                    
                    alert_triggered = 0 <= days_remaining <= 3
                    
                    alert_msg = ""
                    if alert_triggered:
                        alert_msg = f"You may be running out of {medicine.name} in {days_remaining} days. Would you like to refill?"
                    
                    predictions.append(RefillPrediction(
                        user_id=user_id,
                        medicine_name=medicine.name,
                        last_purchase_date=purchase_date,
                        quantity_purchased=quantity,
                        dosage_frequency=dosage_frequency,
                        daily_consumption=daily_consumption,
                        estimated_exhaustion_date=exhaustion_date,
                        days_remaining=days_remaining,
                        alert_triggered=alert_triggered,
                        alert_message=alert_msg,
                        confidence_score=min(score, 1.0)
                    ))
                except Exception as e:
                    print(f"Error predicting for item {item.id}: {e}")
                    
        return predictions

    def get_active_alerts(self, db: Session) -> List[RefillPrediction]:
        """Get all active alerts for all users."""
        predictions = []
        users = db.query(models.User).all()
        for user in users:
            user_predictions = self.predict_refills_for_user(db, user.id)
            for p in user_predictions:
                if p.alert_triggered:
                    predictions.append(p)
        return predictions

    def save_alerts_to_db(self, db: Session, alerts: List[RefillPrediction]):
        """Save predictions to RefillAlert table."""
        for alert in alerts:
            priority = "low"
            if alert.days_remaining <= 1: priority = "high"
            elif alert.days_remaining <= 2: priority = "medium"
            
            new_alert = models.RefillAlert(
                user_id=alert.user_id,
                medicine_name=alert.medicine_name,
                days_remaining=alert.days_remaining,
                exhaustion_date=alert.estimated_exhaustion_date,
                priority=priority,
                confidence_score=alert.confidence_score,
                status="pending"
            )
            db.add(new_alert)
        db.commit()

# Singleton instance
_refill_predictor = None

def get_refill_predictor() -> RefillPredictorAgent:
    """Get or create refill predictor instance"""
    global _refill_predictor
    if _refill_predictor is None:
        _refill_predictor = RefillPredictorAgent()
    return _refill_predictor
