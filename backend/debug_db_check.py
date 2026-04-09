import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Base dir is the script's dir.
# Let's match database.py:
# DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, '..', '..', 'backend-node', 'pharmacy.db')}"
# Wait, if this script is in 'backend', it needs to match.

def check():
    target_db = os.path.join(BASE_DIR, "pharmacy.db")

    if not os.path.exists(target_db):
        print(f"File {target_db} NOT found")
        return
    
    engine = create_engine(f"sqlite:///{target_db}")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    from sqlalchemy import text
    try:
        res = db.execute(text("SELECT id, name, email FROM users")).fetchall()
        print(f"Users in {target_db}:")
        for u in res:
            print(f"  {u[0]} | {u[1]} | {u[2]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
