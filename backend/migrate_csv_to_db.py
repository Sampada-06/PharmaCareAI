import pandas as pd
import sqlite3
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "pharmacy_products.csv")
DB_PATH = os.path.join(BASE_DIR, "pharmacy.db")


def migrate():
    print(f"Starting migration from {CSV_PATH} to {DB_PATH}")
    
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found at {CSV_PATH}")
        return

    # Load CSV
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} products from CSV")

    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Ensure schema has all necessary columns
    try:
        # Check if drug_interactions column exists
        cursor.execute("PRAGMA table_info(medicines)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'drug_interactions' not in columns:
            print("Adding 'drug_interactions' column to medicines table...")
            cursor.execute("ALTER TABLE medicines ADD COLUMN drug_interactions TEXT")
        
        if 'pzn' not in columns:
            print("Adding 'pzn' column to medicines table...")
            cursor.execute("ALTER TABLE medicines ADD COLUMN pzn TEXT")
            
        if 'package_size' not in columns:
            print("Adding 'package_size' column to medicines table...")
            cursor.execute("ALTER TABLE medicines ADD COLUMN package_size TEXT")

    except Exception as e:
        print(f"Warning updating schema: {e}")

    # 2. Clear existing medicines (to avoid duplicates/stale data)
    print("Clearing existing medicines...")
    cursor.execute("DELETE FROM medicines")

    # 3. Insert data
    print("Inserting products into database...")
    insert_sql = """
    INSERT INTO medicines (
        id, name, category, pzn, price, dosage, 
        stock_quantity, expiry_date, description, requires_prescription, drug_interactions
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    for _, row in df.iterrows():
        params = (
            int(row['product_id']),
            row['product_name'],
            row['category'],
            row['pzn'],
            float(row['price']),
            row['package_size'],
            int(row['stock_quantity']),
            row['expiry_date'],
            row['description'],
            1 if str(row['prescription_needed']).lower() == 'yes' else 0,
            row['drug_interactions']
        )
        cursor.execute(insert_sql, params)

    conn.commit()
    print(f"Migration complete! {len(df)} medicines imported.")
    conn.close()

if __name__ == "__main__":
    migrate()
