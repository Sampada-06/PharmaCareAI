import os
import pandas as pd
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(url, key)

DATA_DIR = os.path.join(os.getcwd(), "data")

def clean_row(row):
    """Replace NaN with None for Supabase Compatibility."""
    return {k: (None if pd.isna(v) else v) for k, v in row.items()}

def migrate_medicines():
    print("--- Migrating Pharmacy Products ---")
    file_path = os.path.join(DATA_DIR, "pharmacy_products.csv")
    df = pd.read_csv(file_path)
    
    # Map columns to match schema
    column_mapping = {
        'product_id': 'product_id',
        'product_name': 'product_name',
        'category': 'category',
        'pzn': 'pzn',
        'price': 'price',
        'package_size': 'package_size',
        'stock_quantity': 'stock_quantity',
        'expiry_date': 'expiry_date',
        'description': 'description',
        'prescription_needed': 'requires_prescription',
        'drug_interactions': 'drug_interactions'
    }
    
    # Rename columns that exist
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    data = df.to_dict(orient='records')
    for row in data:
        row = clean_row(row)
        
        # Data conversion
        if row.get('requires_prescription') is not None:
            row['requires_prescription'] = True if str(row['requires_prescription']).lower() == 'yes' else False
        
        if row.get('price') is not None: row['price'] = float(row['price'])
        if row.get('stock_quantity') is not None: row['stock_quantity'] = int(row['stock_quantity'])
        
        try:
            supabase.table("pharmacy_products").upsert(row).execute()
        except Exception as e:
            print(f"Error inserting product {row.get('product_name')}: {e}")

    print(f"DONE: Migrated {len(data)} products")

def migrate_customers():
    print("--- Migrating Customer History ---")
    file_path = os.path.join(DATA_DIR, "customers.csv")
    # This file has metadata in first 4 rows
    df = pd.read_csv(file_path, skiprows=4)
    
    # Map columns to match schema
    column_mapping = {
        'Patient ID': 'patient_id',
        'Patient Age': 'patient_age',
        'Patient Gender': 'patient_gender',
        'Purchase Date': 'purchase_date',
        'Product Name': 'product_name',
        'Quantity': 'quantity',
        'Total Price (EUR)': 'total_price_eur',
        'Dosage Frequency': 'dosage_frequency',
        'Prescription Required': 'prescription_required'
    }
    
    df = df.rename(columns=column_mapping)
    
    data = df.to_dict(orient='records')
    for row in data:
        row = clean_row(row)
        
        # Date conversion
        if row.get('purchase_date'):
            try:
                # Expected format in CSV might be different, let's keep it robust
                dt = pd.to_datetime(row['purchase_date'])
                row['purchase_date'] = dt.isoformat()
            except:
                pass

        try:
            supabase.table("customer_history").upsert(row).execute()
        except Exception as e:
            print(f"Error inserting history for {row.get('patient_id')}: {e}")
            
    print(f"DONE: Migrated {len(data)} customer history records")

def migrate_refill_alerts():
    print("--- Migrating Refill Alerts ---")
    file_path = os.path.join(DATA_DIR, "refill_alerts.csv")
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        data = df.to_dict(orient='records')
        for row in data:
            row = clean_row(row)
            
            # Date conversions
            for col in ['exhaustion_date', 'alert_date']:
                if row.get(col):
                    try:
                        dt = pd.to_datetime(row[col])
                        row[col] = dt.isoformat()
                    except:
                        pass

            try:
                supabase.table("refill_alerts").upsert(row).execute()
            except Exception as e:
                print(f"Error inserting alert {row.get('alert_id')}: {e}")
        print(f"DONE: Migrated {len(data)} refill alerts")

if __name__ == "__main__":
    try:
        # migrate_medicines() # Already migrated
        migrate_customers()
        migrate_refill_alerts()
        print("\nMigration Complete!")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
