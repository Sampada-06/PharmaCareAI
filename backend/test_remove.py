import os
import sys

# Add backend/app to path
base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_path, 'app'))

import models
from database import SessionLocal

def test_remove():
    db = SessionLocal()
    # Let's find *any* item to remove as a test
    item = db.query(models.CartItem).first()
    
    if item:
        uid = item.user_id
        mid = item.medicine_id
        print(f"Found item: medicine_id={mid} for user_id={uid}, qty={item.quantity}")
        db.delete(item)
        db.commit()
        print("Deleted.")
        
        # Verify
        check = db.query(models.CartItem).filter(
            models.CartItem.user_id == uid,
            models.CartItem.medicine_id == mid
        ).first()
        if not check:
            print("Verified deleted.")
        else:
            print("Error: Item still exists!")
    else:
        print("No items in cart table.")
    db.close()

if __name__ == "__main__":
    test_remove()
