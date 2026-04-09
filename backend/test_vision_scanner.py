"""
Test script for Visual Prescription Scanner
Tests both Gemini Vision and OCR fallback methods
"""

import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

def test_scanner():
    """Test the vision scanner with a sample prescription"""
    from app.vision_scanner import get_vision_scanner
    
    print("=" * 60)
    print("🧪 Testing Visual Prescription Scanner")
    print("=" * 60)
    
    scanner = get_vision_scanner()
    
    # Check if Gemini is initialized
    if scanner.model:
        print("✅ Gemini Vision API initialized")
    else:
        print("⚠️  Gemini not available - will use OCR fallback")
    
    print("\n" + "=" * 60)
    print("📝 Test 1: Sample Prescription Text")
    print("=" * 60)
    
    # Create a test image with prescription text
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple prescription image
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add prescription text
        text = """
        Dr. John Smith, MBBS
        City Clinic
        Date: 15-01-2024
        
        Rx:
        1. Paracetamol 500mg - Twice daily
        2. Amoxicillin 250mg - Three times daily
        3. Cetirizine 10mg - Once daily at night
        
        Signature: Dr. Smith
        """
        
        # Draw text (using default font)
        y_position = 50
        for line in text.strip().split('\n'):
            draw.text((50, y_position), line.strip(), fill='black')
            y_position += 40
        
        # Save to bytes
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Test extraction
        result = scanner.extract_medicines_from_image(img_bytes.getvalue())
        
        print(f"\n📊 Extraction Result:")
        print(f"   Success: {result['success']}")
        print(f"   Method: {result.get('method', 'unknown')}")
        print(f"   Medicines found: {len(result.get('medicines', []))}")
        
        if result['success'] and result.get('medicines'):
            print("\n💊 Extracted Medicines:")
            for i, med in enumerate(result['medicines'], 1):
                print(f"\n   {i}. {med['name']}")
                print(f"      Dosage: {med.get('dosage', 'N/A')}")
                print(f"      Frequency: {med.get('frequency', 'N/A')}")
                print(f"      Confidence: {med.get('confidence', 0) * 100:.0f}%")
        else:
            print(f"\n❌ Extraction failed: {result.get('error', 'Unknown error')}")
        
        if result.get('raw_text'):
            print(f"\n📄 Raw extracted text (first 200 chars):")
            print(f"   {result['raw_text'][:200]}...")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📝 Test 2: Pattern Matching")
    print("=" * 60)
    
    # Test pattern extraction
    test_text = """
    Paracetamol 500mg twice daily
    Amoxicillin 250mg three times a day
    Ibuprofen 400mg as needed
    """
    
    medicines = scanner._extract_medicines_from_text(test_text)
    print(f"\n   Found {len(medicines)} medicines using pattern matching:")
    for med in medicines:
        print(f"   - {med.name} ({med.confidence * 100:.0f}% confidence)")
    
    print("\n" + "=" * 60)
    print("✅ Testing Complete!")
    print("=" * 60)
    
    # Print usage instructions
    print("\n📖 How to use:")
    print("   1. Start backend: uvicorn app.main:app --reload --port 8000")
    print("   2. Open: frontend/prescription-scanner.html")
    print("   3. Upload a prescription image")
    print("   4. View extracted medicines with confidence scores")
    
    print("\n💡 Tips:")
    print("   - Ensure GEMINI_API_KEY is set in .env for best results")
    print("   - Install Tesseract OCR for fallback support")
    print("   - Use clear, well-lit prescription images")
    print("   - Supported formats: JPG, PNG, HEIC, WebP")


if __name__ == "__main__":
    test_scanner()
