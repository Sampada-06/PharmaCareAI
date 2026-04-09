from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Base dir is backend/app/
# We want the db in backend/
# We want to use the shared database in backend-node/
db_path = os.path.abspath(os.path.join(BASE_DIR, "..", "pharmacy.db")).replace("\\", "/")
# On Windows, abspath might start with C:/, resulting in sqlite:///C:/... which has 3 slashes.
# This is usually correct for SQLAlchemy.
DATABASE_URL = f"sqlite:///{db_path}"

print(f"DEBUG: Database URL is {DATABASE_URL}")
print(f"DEBUG: Files exists? {os.path.exists(db_path)}")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()