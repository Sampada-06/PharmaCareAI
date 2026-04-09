"""
Background Scheduler for Refill Predictions
Runs daily to check for refill needs and generate alerts
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app.refill_predictor import get_refill_predictor
from app.database import SessionLocal
from app.models import User
from app.email_service import send_refill_alert_email, send_low_stock_email
from app.supabase_client import supabase
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RefillScheduler:
    """Background scheduler for refill predictions"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.predictor = None
    
    def daily_refill_check(self):
        """
        Daily job to check refill needs
        Runs every day at 9:00 AM
        """
        db = SessionLocal()
        try:
            logger.info("Starting daily refill check...")
            
            # Get predictor instance
            if self.predictor is None:
                self.predictor = get_refill_predictor()
            
            # Get all active alerts
            alerts = self.predictor.get_active_alerts(db)
            
            logger.info(f"Found {len(alerts)} active refill alerts")
            
            if alerts:
                # Log summary and send emails
                for alert in alerts:
                    logger.info(
                        f"Alert: {alert.user_id} - {alert.medicine_name} "
                        f"({alert.days_remaining} days remaining)"
                    )
                    user = db.query(User).filter(User.id == alert.user_id).first()
                    if user and user.email:
                        email_data = {
                            "medicine_name": alert.medicine_name,
                            "days_remaining": alert.days_remaining
                        }
                        send_refill_alert_email(user.email, email_data)
            else:
                logger.info("OK: No refill alerts needed today")
                
            # --- LOW STOCK CHECK ALERTS (Pharmacist) ---
            logger.info("Starting checks for low-stock inventory alerts in Supabase...")
            if supabase:
                try:
                    response = supabase.table("pharmacy_products").select("product_id, product_name, stock_quantity").lt("stock_quantity", 20).execute()
                    low_stock_items_raw = response.data or []
                    
                    if low_stock_items_raw:
                        formatted_low_stock = [
                            {"name": item["product_name"], "stock_qty": item["stock_quantity"]}
                            for item in low_stock_items_raw
                        ]
                        
                        logger.info(f"Found {len(formatted_low_stock)} low stock items in Supabase")
                        
                        pharmacist_email = os.getenv("PHARMACIST_EMAIL", os.getenv("EMAIL_USER"))
                        if pharmacist_email:
                            send_low_stock_email(pharmacist_email, formatted_low_stock)
                        else:
                            logger.warning("No pharmacist email configured for alerts.")
                    else:
                        logger.info("OK: No low stock found under threshold 20")
                except Exception as e:
                    logger.error(f"Failed to check Supabase low stock: {e}")
            else:
                logger.warning("Supabase client not initialized, skipping low stock emails.")
            
            logger.info("OK: Daily check tasks completed")
            
        except Exception as e:
            logger.error(f"Error in daily refill check: {e}")
        finally:
            db.close()
    
    def start(self):
        """Start the scheduler"""
        # Schedule daily job at 9:00 AM
        self.scheduler.add_job(
            self.daily_refill_check,
            trigger=CronTrigger(hour=9, minute=0),
            id='daily_refill_check',
            name='Daily Refill Prediction Check',
            replace_existing=True
        )
        
        # Also run immediately on startup for testing
        self.scheduler.add_job(
            self.daily_refill_check,
            id='startup_refill_check',
            name='Startup Refill Check'
        )
        
        self.scheduler.start()
        logger.info("OK: Refill scheduler started (runs daily at 9:00 AM)")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("STOP: Refill scheduler stopped")
    
    def run_now(self):
        """Manually trigger refill check (for testing)"""
        self.daily_refill_check()


# Singleton instance
_scheduler = None

def get_scheduler() -> RefillScheduler:
    """Get or create scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = RefillScheduler()
    return _scheduler

def start_scheduler():
    """Start the background scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler

def stop_scheduler():
    """Stop the background scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
