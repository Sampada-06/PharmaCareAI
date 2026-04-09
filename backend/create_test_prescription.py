"""
Generate a test prescription image for testing the Visual Scanner
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_prescription():
    """Create a realistic test prescription image"""
    
    # Create image
    width, height = 800, 1000
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a better font, fallback to default
    try:
        # Try common font paths
        font_paths = [
            "C:\\Windows\\Fonts\\arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        title_font = None
        text_font = None
        
        for path in font_paths:
            if os.path.exists(path):
                title_font = ImageFont.truetype(path, 24)
                text_font = ImageFont.truetype(path, 18)
                break
        
        if not title_font:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            
    except Exception as e:
        print(f"Using default font: {e}")
        title_font = ImageFont.load_default()
        text_font = ImageFont.load_default()
    
    # Draw header
    draw.rectangle([(0, 0), (width, 120)], fill='#667eea')
    draw.text((50, 30), "City Medical Clinic", fill='white', font=title_font)
    draw.text((50, 65), "Dr. Rajesh Kumar, MBBS, MD", fill='white', font=text_font)
    draw.text((50, 90), "Reg. No: MH-12345", fill='white', font=text_font)
    
    # Patient info
    y = 160
    draw.text((50, y), "Patient Name: Sampada Raut", fill='black', font=text_font)
    y += 35
    draw.text((50, y), "Age: 28 years", fill='black', font=text_font)
    y += 35
    draw.text((50, y), "Date: 15-01-2024", fill='black', font=text_font)
    
    # Prescription header
    y += 60
    draw.text((50, y), "Rx", fill='#667eea', font=title_font)
    
    # Medicines
    y += 50
    medicines = [
        "1. Tab. Paracetamol 500mg",
        "   Dosage: 1 tablet twice daily after meals",
        "   Duration: 5 days",
        "",
        "2. Cap. Amoxicillin 250mg",
        "   Dosage: 1 capsule three times daily",
        "   Duration: 7 days",
        "",
        "3. Tab. Cetirizine 10mg",
        "   Dosage: 1 tablet once daily at night",
        "   Duration: 10 days",
        "",
        "4. Syrup Crocin 120ml",
        "   Dosage: 10ml when needed for fever",
        "   (Maximum 3 times a day)",
    ]
    
    for line in medicines:
        draw.text((50, y), line, fill='black', font=text_font)
        y += 30
    
    # Instructions
    y += 30
    draw.text((50, y), "General Instructions:", fill='#667eea', font=text_font)
    y += 35
    instructions = [
        "• Take medicines after meals",
        "• Drink plenty of water",
        "• Complete the full course",
        "• Consult if symptoms persist"
    ]
    
    for instruction in instructions:
        draw.text((50, y), instruction, fill='black', font=text_font)
        y += 30
    
    # Signature
    y += 40
    draw.text((50, y), "Dr. Rajesh Kumar", fill='black', font=text_font)
    y += 30
    draw.text((50, y), "Signature: _______________", fill='black', font=text_font)
    
    # Footer
    draw.rectangle([(0, height-60), (width, height)], fill='#f0f0f0')
    draw.text((50, height-40), "Contact: +91 98765 43210 | Email: clinic@example.com", 
              fill='#666', font=text_font)
    
    # Save
    output_path = "test_prescription.png"
    img.save(output_path)
    print(f"✅ Test prescription created: {output_path}")
    print(f"   Size: {width}x{height}px")
    print(f"   Medicines: 4")
    print(f"\n📝 Expected extraction:")
    print("   1. Paracetamol 500mg - twice daily")
    print("   2. Amoxicillin 250mg - three times daily")
    print("   3. Cetirizine 10mg - once daily at night")
    print("   4. Crocin 120ml - when needed")
    print(f"\n💡 Use this image to test the scanner:")
    print(f"   1. Open: frontend/prescription-scanner.html")
    print(f"   2. Upload: {output_path}")
    print(f"   3. Verify: All 4 medicines extracted")
    
    return output_path

if __name__ == "__main__":
    create_test_prescription()
