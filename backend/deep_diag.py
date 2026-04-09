import sys
import os
import traceback

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import models, auth
    from app.database import engine, Base, SessionLocal
    import uuid
except Exception as e:
    print(f"FAILED TO IMPORT: {e}")
    traceback.print_exc()
    sys.exit(1)

def run_diag():
    print("Starting Deep Auth Diagnostic...")
    
    # 1. Create Tables
    print("\n1. Creating tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables Created (or already exist)")
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        traceback.print_exc()
        return

    # 2. Insert User
    print("\n2. Inserting user...")
    db = SessionLocal()
    try:
        email = f"diag_{uuid.uuid4().hex[:6]}@test.com"
        new_user = models.User(
            name="Diag User",
            email=email,
            phone="000",
            hashed_password=auth.get_password_hash("pass")
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"✅ User inserted successfully: {new_user.email}, ID: {new_user.id}")
    except Exception as e:
        print(f"❌ User insertion failed: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_diag()
