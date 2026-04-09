"""
List available Gemini models
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv("backend/.env")

api_key = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'").strip()
genai.configure(api_key=api_key)

print("Available Gemini models that support generateContent:\n")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ {model.name}")
        print(f"   Display name: {model.display_name}")
        print(f"   Description: {model.description[:100] if model.description else 'N/A'}")
        print()
