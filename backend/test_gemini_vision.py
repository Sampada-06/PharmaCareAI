"""
Quick test to verify Gemini Vision API is working
"""
import os
from dotenv import load_dotenv

# Load environment
load_dotenv("backend/.env")

# Test Gemini Vision
try:
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'").strip()
    print(f"API Key found: {api_key[:20]}...")
    
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment")
        exit(1)
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Try to create model
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    print("✅ Gemini model created successfully")
    
    # Try a simple text generation
    response = model.generate_content("Say 'Hello, I am working!'")
    print(f"✅ Gemini response: {response.text}")
    
    print("\n✅ Gemini Vision API is working correctly!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Install: pip install google-generativeai")
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")
