"""
Migration script to add prescription fields to Order table
Run this once to update existing database schema
"""
import sqlite3
import os

# Database path - using the same path as the application
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "pharmacy.db")


def migrate_order_table():
    """Add prescription fields to orders table"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        print("Please ensure the backend has been run at least once to create the database.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # List of new columns to add
    new_columns = [
        ("prescription_url", "TEXT"),
        ("prescription_required", "INTEGER DEFAULT 0")
    ]
    
    print(f"🔄 Starting Order table migration on: {DB_PATH}")
    
    for column_name, column_type in new_columns:
        try:
            # Check if column exists
            cursor.execute(f"PRAGMA table_info(orders)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if column_name not in columns:
                # Add the column
                cursor.execute(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")
                print(f"✅ Added column: {column_name}")
            else:
                print(f"⏭️  Column already exists: {column_name}")
        except Exception as e:
            print(f"❌ Error adding column {column_name}: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate_order_table()
