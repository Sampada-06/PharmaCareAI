"""
Test the fixed vision scanner with Gemini 2.0 Flash
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from dotenv import load_dotenv
load_dotenv("backend/.env")

from app.vision_scanner import get_vision_scanner
from PIL import Image, ImageDraw, ImageFont
import io

# Create a simple test prescription image
def create_test_prescription():
    """Create a simple prescription image for testing"""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fallback to default if not available
    try:
        font_large = ImageFont.truetype("arial.ttf", 32)
        font_medium = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw prescription header
    draw.text((50, 30), "Dr. Smith Medical Clinic", fill='black', font=font_large)
    draw.text((50, 80), "Prescription", fill='blue', font=font_medium)
    draw.line([(50, 110), (750, 110)], fill='black', width=2)
    
    # Draw medicines
    y = 150
    medicines = [
        "Paracetamol 500mg - Take twice daily",
        "Amoxicillin 250mg - Take three times daily",
        "Cetirizine 10mg - Take once daily at bedtime"
    ]
    
    for med in medicines:
        draw.text((70, y), f"• {med}", fill='black', font=font_small)
        y += 50
    
    # Draw footer
    draw.text((50, 500), "Dr. John Smith", fill='black', font=font_medium)
    draw.text((50, 530), "Date: 28-02-2026", fill='gray', font=font_small)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

print("Creating test prescription image...")
test_image = create_test_prescription()
print(f"✅ Test image created ({len(test_image)} bytes)")

print("\nInitializing vision scanner...")
scanner = get_vision_scanner()

if scanner.model:
    print("✅ Gemini Vision model initialized")
else:
    print("⚠️ Gemini Vision not available, will use OCR fallback")

print("\nScanning prescription...")
result = scanner.extract_medicines_from_image(test_image)

print("\n" + "="*60)
print("SCAN RESULTS:")
print("="*60)
print(f"Success: {result['success']}")
print(f"Method: {result.get('method', 'unknown')}")

if result['success']:
    print(f"\nExtracted {len(result['medicines'])} medicines:")
    for i, med in enumerate(result['medicines'], 1):
        print(f"\n{i}. {med['name']}")
        print(f"   Dosage: {med.get('dosage', 'N/A')}")
        print(f"   Frequency: {med.get('frequency', 'N/A')}")
        print(f"   Confidence: {med.get('confidence', 0)*100:.0f}%")
    
    if result.get('doctor_name'):
        print(f"\nDoctor: {result['doctor_name']}")
    if result.get('date'):
        print(f"Date: {result['date']}")
else:
    print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
    if result.get('help'):
        print("\nSuggested solutions:")
        for key, value in result['help'].items():
            print(f"  • {value}")

print("\n" + "="*60)
