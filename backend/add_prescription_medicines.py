"""
Script to mark some medicines as requiring prescriptions
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from core.supabase_client import supabase

def add_prescription_requirements():
    """Mark antibiotics and strong medicines as requiring prescriptions"""
    
    print("=" * 60)
    print("Adding Prescription Requirements to Medicines")
    print("=" * 60)
    
    if not supabase:
        print("❌ Supabase not initialized")
        return
    
    # Medicines that should require prescriptions (antibiotics, strong painkillers, etc.)
    prescription_keywords = [
        'Amoxicillin', 'Azithromycin', 'Ciprofloxacin', 'Doxycycline',
        'Metronidazole', 'Cephalexin', 'Penicillin', 'Erythromycin',
        'Tramadol', 'Codeine', 'Morphine', 'Oxycodone',
        'Alprazolam', 'Diazepam', 'Lorazepam', 'Clonazepam',
        'Insulin', 'Metformin', 'Warfarin', 'Prednisone'
    ]
    
    # Get all medicines
    print("\n1. Fetching all medicines...")
    response = supabase.table("pharmacy_products").select("*").execute()
    medicines = response.data
    print(f"✓ Found {len(medicines)} medicines")
    
    # Update medicines that match prescription keywords
    print("\n2. Updating medicines to require prescriptions...")
    updated_count = 0
    
    for med in medicines:
        product_name = med.get('product_name', '')
        category = med.get('category', '')
        
        # Check if medicine should require prescription
        should_require_rx = False
        
        # Check by name
        for keyword in prescription_keywords:
            if keyword.lower() in product_name.lower():
                should_require_rx = True
                break
        
        # Check by category
        if category in ['Antibiotic', 'Prescription', 'Controlled Substance']:
            should_require_rx = True
        
        # Update if needed
        if should_require_rx and not med.get('requires_prescription'):
            try:
                supabase.table("pharmacy_products").update({
                    "requires_prescription": True
                }).eq("product_id", med['product_id']).execute()
                
                print(f"  ✓ {product_name} (ID: {med['product_id']}) - Now requires prescription")
                updated_count += 1
            except Exception as e:
                print(f"  ❌ Failed to update {product_name}: {str(e)}")
    
    print(f"\n3. Summary:")
    print(f"  - Total medicines: {len(medicines)}")
    print(f"  - Updated to require prescription: {updated_count}")
    
    # Show some examples
    print("\n4. Examples of prescription-required medicines:")
    response = supabase.table("pharmacy_products").select("product_id, product_name, category").eq("requires_prescription", True).limit(5).execute()
    for med in response.data:
        print(f"  - {med['product_name']} (Category: {med.get('category', 'N/A')})")
    
    print("\n" + "=" * 60)
    print("✅ Prescription requirements added successfully!")
    print("=" * 60)

if __name__ == "__main__":
    add_prescription_requirements()
