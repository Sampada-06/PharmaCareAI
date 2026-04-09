-- SQL Schema for Pharmacy App

-- 1. Pharmacy Products Table
CREATE TABLE IF NOT EXISTS pharmacy_products (
    id SERIAL PRIMARY KEY,
    product_id INTEGER,
    product_name TEXT NOT NULL,
    category TEXT,
    pzn TEXT,
    price DECIMAL(10,2) NOT NULL,
    package_size TEXT,
    stock_quantity INTEGER DEFAULT 0,
    expiry_date DATE,
    description TEXT,
    requires_prescription BOOLEAN DEFAULT FALSE,
    drug_interactions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users Table (Simplified if not using Supabase Auth)
CREATE TABLE IF NOT EXISTS customer_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    date_of_birth DATE,
    address TEXT,
    role TEXT DEFAULT 'customer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Customer History Table (from customers.csv)
CREATE TABLE IF NOT EXISTS customer_history (
    id SERIAL PRIMARY KEY,
    patient_id TEXT,
    patient_age INTEGER,
    patient_gender TEXT,
    purchase_date TIMESTAMP WITH TIME ZONE,
    product_name TEXT,
    quantity INTEGER,
    total_price_eur DECIMAL(10,2),
    dosage_frequency TEXT,
    prescription_required TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_status TEXT DEFAULT 'pending',
    order_status TEXT DEFAULT 'processing',
    prescription_url TEXT,
    prescription_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Order Items Table
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id TEXT REFERENCES orders(id),
    medicine_id INTEGER REFERENCES pharmacy_products(id),
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

-- 6. Refill Alerts Table
CREATE TABLE IF NOT EXISTS refill_alerts (
    id SERIAL PRIMARY KEY,
    alert_id TEXT UNIQUE,
    patient_id TEXT,
    medicine_name TEXT NOT NULL,
    days_remaining INTEGER,
    exhaustion_date TIMESTAMP WITH TIME ZONE,
    alert_date TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'pending',
    priority TEXT,
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
