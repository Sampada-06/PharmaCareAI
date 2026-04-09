"""
Visual Prescription Scanner with AI
Extracts medicine names from prescription images using Gemini Vision API
Provides confidence scores and structured extraction results
"""

import os
import logging
from typing import List, Dict, Optional
from PIL import Image
import io
import base64
import json
import re

logger = logging.getLogger(__name__)

class MedicineExtraction:
    """Structured medicine extraction result"""
    def __init__(self, name: str, dosage: str = "", frequency: str = "", confidence: float = 0.0):
        self.name = name
        self.dosage = dosage
        self.frequency = frequency
        self.confidence = confidence
    
    def to_dict(self):
        return {
            "name": self.name,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 2)
        }


class VisionScanner:
    """AI-powered prescription scanner using Gemini Vision"""
    
    def __init__(self):
        self.model = None
        self._init_gemini()
    
    def _init_gemini(self):
        """Initialize Gemini Vision model"""
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'").strip()
            
            if not api_key:
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'").strip()
            
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                logger.info("✅ Gemini Vision initialized successfully")
            else:
                logger.warning("⚠️ GEMINI_API_KEY not found. Vision scanner will use fallback OCR.")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini Vision: {e}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR detection
        Handles dark, blurry, low-contrast images
        """
        try:
            from PIL import ImageEnhance, ImageFilter, ImageOps
            import numpy as np
            import cv2
            
            # Convert PIL to numpy array for advanced processing
            img_array = np.array(image)
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # 1. Increase brightness for dark images
            # Calculate average brightness
            avg_brightness = np.mean(gray)
            logger.info(f"📊 Image brightness: {avg_brightness:.1f}/255")
            
            if avg_brightness < 100:  # Dark image
                # Increase brightness significantly
                brightness_factor = 150 / avg_brightness if avg_brightness > 0 else 2.0
                brightness_factor = min(brightness_factor, 3.0)  # Cap at 3x
                gray = cv2.convertScaleAbs(gray, alpha=brightness_factor, beta=30)
                logger.info(f"✨ Brightened dark image by {brightness_factor:.1f}x")
            
            # 2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            # This dramatically improves contrast in dark/uneven lighting
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            logger.info("✨ Applied CLAHE for adaptive contrast")
            
            # 3. Denoise
            gray = cv2.fastNlMeansDenoising(gray, h=10)
            logger.info("✨ Denoised image")
            
            # 4. Sharpen
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            gray = cv2.filter2D(gray, -1, kernel)
            logger.info("✨ Sharpened image")
            
            # 5. Use Otsu's thresholding for better text separation
            # This automatically finds the best threshold value
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            logger.info("✨ Applied Otsu's thresholding")
            
            # 6. Morphological operations to clean up text
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            logger.info("✨ Cleaned up text with morphology")
            
            # Convert back to PIL Image
            image_enhanced = Image.fromarray(binary)
            
            # Convert to RGB for compatibility
            image_enhanced = image_enhanced.convert('RGB')
            
            logger.info("✅ Image preprocessing complete (dark image optimized)")
            return image_enhanced
            
        except ImportError:
            logger.warning("⚠️ OpenCV not available, using basic preprocessing")
            # Fallback to basic PIL processing
            try:
                from PIL import ImageEnhance, ImageFilter
                
                # Convert to grayscale
                image = image.convert('L')
                
                # Increase brightness for dark images
                enhancer = ImageEnhance.Brightness(image)
                image = enhancer.enhance(2.0)
                
                # Increase contrast
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(2.5)
                
                # Increase sharpness
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(2.0)
                
                # Denoise
                image = image.filter(ImageFilter.MedianFilter(size=3))
                
                # Convert back to RGB
                image = image.convert('RGB')
                
                logger.info("✅ Basic image preprocessing complete")
                return image
            except Exception as e:
                logger.warning(f"⚠️ Basic preprocessing failed: {e}, using original")
                return image
                
        except Exception as e:
            logger.warning(f"⚠️ Image preprocessing failed: {e}, using original")
            return image
    
    def _search_in_database(self, result: Dict) -> Dict:
        """
        Search extracted medicine names in Supabase database
        Finds actual products and adds database info
        """
        try:
            from app.supabase_client import supabase
            
            if not supabase:
                logger.warning("⚠️ Supabase not available for database search")
                return result
            
            medicines = result.get("medicines", [])
            if not medicines:
                return result
            
            logger.info(f"🔍 Searching {len(medicines)} medicines in database...")
            
            found_products = []
            not_found = []
            
            for med in medicines:
                medicine_name = med.get("name", "").strip()
                if not medicine_name:
                    continue
                
                # Search in database with fuzzy matching
                # Try exact match first
                response = supabase.table("pharmacy_products").select("*").ilike("product_name", f"%{medicine_name}%").limit(5).execute()
                
                if response.data and len(response.data) > 0:
                    # Found matches
                    for product in response.data:
                        found_products.append({
                            "extracted_name": medicine_name,
                            "product_id": product.get("product_id"),
                            "product_name": product.get("product_name"),
                            "price": product.get("price"),
                            "stock_quantity": product.get("stock_quantity"),
                            "category": product.get("category"),
                            "requires_prescription": product.get("requires_prescription", False),
                            "dosage": med.get("dosage", ""),
                            "frequency": med.get("frequency", ""),
                            "confidence": med.get("confidence", 0.0),
                            "match_type": "exact" if medicine_name.lower() in product.get("product_name", "").lower() else "partial"
                        })
                    logger.info(f"✅ Found {len(response.data)} matches for '{medicine_name}'")
                else:
                    # Try partial match with individual words
                    words = medicine_name.split()
                    for word in words:
                        if len(word) >= 4:  # Only search words with 4+ characters
                            response = supabase.table("pharmacy_products").select("*").ilike("product_name", f"%{word}%").limit(3).execute()
                            if response.data and len(response.data) > 0:
                                for product in response.data:
                                    found_products.append({
                                        "extracted_name": medicine_name,
                                        "product_id": product.get("product_id"),
                                        "product_name": product.get("product_name"),
                                        "price": product.get("price"),
                                        "stock_quantity": product.get("stock_quantity"),
                                        "category": product.get("category"),
                                        "requires_prescription": product.get("requires_prescription", False),
                                        "dosage": med.get("dosage", ""),
                                        "frequency": med.get("frequency", ""),
                                        "confidence": med.get("confidence", 0.0) * 0.7,  # Lower confidence for partial match
                                        "match_type": "fuzzy"
                                    })
                                logger.info(f"✅ Found fuzzy matches for '{medicine_name}' using word '{word}'")
                                break
                    
                    if not any(p["extracted_name"] == medicine_name for p in found_products):
                        not_found.append(medicine_name)
                        logger.warning(f"❌ No matches found for '{medicine_name}'")
            
            # Update result with database matches
            result["database_matches"] = found_products
            result["not_found_in_db"] = not_found
            result["found_count"] = len(found_products)
            result["searched_count"] = len(medicines)
            
            logger.info(f"🎯 Database search complete: {len(found_products)} products found, {len(not_found)} not found")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Database search failed: {e}")
            # Return original result if database search fails
            return result
    
    def extract_medicines_from_image(self, image_bytes: bytes) -> Dict:
        """
        Extract medicine names, dosages, and frequencies from prescription image
        Then search in Supabase database for actual products
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Dict with extracted medicines, confidence scores, and database matches
        """
        try:
            # Load and validate image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhance image for better OCR (preprocessing)
            image = self._preprocess_image(image)
            
            # Resize if too large (max 4MB for Gemini)
            max_size = (2048, 2048)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Try Gemini Vision first
            if self.model:
                result = self._extract_with_gemini(image)
                if result["success"]:
                    # Search in database for actual products
                    result = self._search_in_database(result)
                    return result
            
            # Fallback to OCR + pattern matching
            result = self._extract_with_ocr(image)
            if result["success"]:
                # Search in database for actual products
                result = self._search_in_database(result)
            return result
            
        except Exception as e:
            logger.error(f"❌ Image extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "medicines": [],
                "raw_text": "",
                "method": "error"
            }
    
    def _extract_with_gemini(self, image: Image.Image) -> Dict:
        """Extract medicines using Gemini Vision API"""
        try:
            prompt = """Analyze this prescription image and extract ALL medicine names with their details.

CRITICAL RULES:
1. Extract ONLY medicine names (brand or generic)
2. Include dosage (e.g., 500mg, 10ml, 250mcg)
3. Include frequency (e.g., "twice daily", "once daily", "as needed")
4. Provide confidence score (0-100) for each medicine
5. Ignore doctor name, patient name, clinic details
6. Return ONLY valid JSON, no markdown, no explanation

OUTPUT FORMAT (JSON only):
{
  "medicines": [
    {
      "name": "Medicine Name",
      "dosage": "500mg",
      "frequency": "twice daily",
      "confidence": 95
    }
  ],
  "doctor_name": "Dr. Name (if visible)",
  "date": "DD-MM-YYYY (if visible)"
}

If no medicines found, return: {"medicines": [], "doctor_name": "", "date": ""}
"""
            
            response = self.model.generate_content(
                [prompt, image],
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 1000,
                }
            )
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini")
            
            # Clean response (remove markdown if present)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Parse JSON
            data = json.loads(text)
            
            # Validate and structure
            medicines = []
            for med in data.get("medicines", []):
                if med.get("name"):
                    medicines.append(MedicineExtraction(
                        name=med["name"],
                        dosage=med.get("dosage", ""),
                        frequency=med.get("frequency", ""),
                        confidence=float(med.get("confidence", 85)) / 100.0
                    ))
            
            logger.info(f"✅ Gemini Vision extracted {len(medicines)} medicines")
            
            return {
                "success": True,
                "medicines": [m.to_dict() for m in medicines],
                "doctor_name": data.get("doctor_name", ""),
                "date": data.get("date", ""),
                "raw_text": text,
                "method": "gemini_vision"
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Gemini returned invalid JSON: {e}")
            logger.error(f"Response text: {response.text if response else 'None'}")
            return {"success": False, "error": "Invalid JSON from AI"}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Gemini Vision extraction failed: {e}")
            
            # Check if it's a quota error
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Gemini API quota exceeded. Please wait a few minutes or install Tesseract OCR as fallback.",
                    "help": {
                        "option1": "Wait 1-2 minutes and try again (free tier rate limit)",
                        "option2": "Install Tesseract OCR: Download from https://github.com/UB-Mannheim/tesseract/wiki",
                        "option3": "Or use a different Gemini API key with higher quota"
                    },
                    "method": "gemini_quota_exceeded"
                }
            
            return {"success": False, "error": str(e)}
    
    def _extract_with_ocr(self, image: Image.Image) -> Dict:
        """Fallback: Extract using OCR + pattern matching"""
        try:
            ocr_text = ""
            ocr_method = "none"
            
            # Try Pytesseract first
            try:
                import pytesseract
                # Try to find Tesseract executable
                tess_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Users\\' + os.getlogin() + r'\AppData\Local\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
                ]
                
                tesseract_found = False
                for p in tess_paths:
                    if os.path.exists(p):
                        pytesseract.pytesseract.tesseract_cmd = p
                        tesseract_found = True
                        break
                
                if tesseract_found:
                    # Enhanced OCR configuration for complete word extraction
                    # PSM 6 = Uniform block of text (best for prescriptions)
                    # OEM 1 = LSTM neural net mode (better word recognition)
                    # Preserve interword spaces to keep words intact
                    custom_config = r'--oem 1 --psm 6 -c preserve_interword_spaces=1'
                    ocr_text = pytesseract.image_to_string(image, config=custom_config, lang='eng')
                    
                    # If first attempt fails or gets little text, try different PSM mode
                    if len(ocr_text.strip()) < 20:
                        logger.info("⚠️ First OCR attempt got little text, trying PSM 11 (sparse text)")
                        custom_config = r'--oem 1 --psm 11 -c preserve_interword_spaces=1'
                        ocr_text = pytesseract.image_to_string(image, config=custom_config, lang='eng')
                    
                    # If still poor results, try PSM 3 (fully automatic)
                    if len(ocr_text.strip()) < 20:
                        logger.info("⚠️ Trying PSM 3 (fully automatic page segmentation)")
                        custom_config = r'--oem 1 --psm 3 -c preserve_interword_spaces=1'
                        ocr_text = pytesseract.image_to_string(image, config=custom_config, lang='eng')
                    
                    ocr_method = "pytesseract"
                    logger.info(f"✅ OCR: Pytesseract successful ({len(ocr_text)} characters extracted)")
                    logger.info(f"📝 Extracted text preview: {ocr_text[:200]}...")
                else:
                    raise Exception("Tesseract executable not found")
                    
            except Exception as e:
                logger.warning(f"⚠️ Pytesseract failed: {e}")
                
                # Try EasyOCR as fallback
                try:
                    import easyocr
                    import numpy as np
                    reader = easyocr.Reader(['en'], gpu=False)
                    results = reader.readtext(np.array(image))
                    ocr_text = " ".join([res[1] for res in results])
                    ocr_method = "easyocr"
                    logger.info("✅ OCR: EasyOCR successful")
                except Exception as e2:
                    logger.error(f"❌ EasyOCR also failed: {e2}")
                    # Return helpful error message
                    return {
                        "success": False,
                        "error": "OCR libraries not available. Please use Gemini Vision by setting GEMINI_API_KEY in .env file, or install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki",
                        "medicines": [],
                        "raw_text": "",
                        "method": "ocr_failed",
                        "help": {
                            "option1": "Set GEMINI_API_KEY in backend/.env for AI extraction",
                            "option2": "Install Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki",
                            "option3": "Install EasyOCR: pip install easyocr"
                        }
                    }
            
            if not ocr_text:
                return {
                    "success": False,
                    "error": "No text could be extracted from the image",
                    "medicines": [],
                    "raw_text": "",
                    "method": "ocr_no_text"
                }
            
            # Pattern matching for medicine names
            medicines = self._extract_medicines_from_text(ocr_text)
            
            if not medicines:
                logger.warning(f"⚠️ No medicines found in text: {ocr_text[:200]}")
                return {
                    "success": False,
                    "error": "No medicine names found in the extracted text. Please ensure the image contains clear medicine names.",
                    "medicines": [],
                    "raw_text": ocr_text[:500],  # Show more text for debugging
                    "method": ocr_method,
                    "help": {
                        "tip1": "Try using a clearer image with better lighting",
                        "tip2": "Ensure medicine names are clearly visible and not blurry",
                        "tip3": "Position the prescription flat without shadows",
                        "extracted_text": ocr_text[:200]  # Show what was extracted
                    }
                }
            
            return {
                "success": True,
                "medicines": [m.to_dict() for m in medicines],
                "doctor_name": "",
                "date": "",
                "raw_text": ocr_text,
                "method": f"ocr_pattern_matching_{ocr_method}"
            }
            
        except Exception as e:
            logger.error(f"❌ OCR extraction failed: {e}")
            return {
                "success": False,
                "error": f"OCR extraction error: {str(e)}",
                "medicines": [],
                "raw_text": "",
                "method": "error"
            }
    
    def _extract_medicines_from_text(self, text: str) -> List[MedicineExtraction]:
        """Extract medicine names from OCR text using pattern matching"""
        medicines = []
        
        logger.info(f"📝 Extracted OCR text (first 500 chars): {text[:500]}")
        
        # Expanded medicine patterns - more flexible
        medicine_patterns = [
            # Common suffixes
            r'\b([A-Z][a-z]+(?:cillin|mycin|zole|prazole|dipine|sartan|olol|statin|formin|xin|dine|pine|mab|nib))\b',
            # Common medicine names (expanded list)
            r'\b(Paracetamol|Aspirin|Ibuprofen|Amoxicillin|Azithromycin|Cetirizine|Metformin|Omeprazole|Pantoprazole|Ranitidine|Ciprofloxacin|Doxycycline|Clopidogrel|Atorvastatin|Simvastatin|Amlodipine|Losartan|Enalapril|Lisinopril|Furosemide|Hydrochlorothiazide|Salbutamol|Montelukast|Prednisolone|Dexamethasone|Insulin|Glimepiride|Levothyroxine|Diclofenac|Tramadol|Gabapentin|Alprazolam|Lorazepam|Sertraline|Fluoxetine|Vitamin|Calcium|Iron|Zinc|Folic|Multivitamin)\b',
            # Name + dosage pattern
            r'\b([A-Z][a-z]{3,})\s+\d+\s*(?:mg|ml|mcg|g|iu)\b',
            # Capitalized words (3+ letters) - more flexible
            r'\b([A-Z][a-z]{2,}[A-Z]?[a-z]*)\b',
            # Words ending in common medicine suffixes
            r'\b(\w+(?:ol|in|ide|ate|one|ine))\b',
        ]
        
        # Dosage pattern
        dosage_pattern = r'\b(\d+(?:\.\d+)?)\s*(mg|ml|mcg|g|iu|units?)\b'
        
        # Frequency patterns
        frequency_patterns = [
            r'\b(once|twice|thrice|three times?)\s+(?:a\s+)?(?:daily|day)\b',
            r'\b(\d+)\s*(?:times?|x)\s*(?:a\s+)?(?:daily|day)\b',
            r'\b(morning|evening|night|bedtime|as needed|after meals?|before meals?)\b',
            r'\b(OD|BD|TDS|QDS|PRN|SOS)\b',  # Medical abbreviations
        ]
        
        # Words to skip (not medicines)
        skip_words = {
            'dr', 'doctor', 'clinic', 'hospital', 'patient', 'name', 'age', 'date',
            'prescription', 'rx', 'address', 'phone', 'email', 'the', 'and', 'for',
            'with', 'take', 'tablet', 'capsule', 'syrup', 'injection', 'cream',
            'ointment', 'drops', 'spray', 'inhaler', 'powder', 'solution'
        }
        
        lines = text.split('\n')
        found_words = set()  # Track found medicines to avoid duplicates
        
        for line in lines:
            line = line.strip()
            
            # Skip very short lines
            if len(line) < 3:
                continue
            
            # Skip lines with common non-medicine keywords
            line_lower = line.lower()
            if any(skip in line_lower for skip in ['dr.', 'clinic', 'hospital', 'patient name', 'date:', 'age:', 'address']):
                continue
            
            logger.debug(f"Processing line: {line}")
            
            # Try to find medicine names
            for pattern in medicine_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    name = match.group(1).strip()
                    name_lower = name.lower()
                    
                    # Skip if already found or in skip list
                    if name_lower in found_words or name_lower in skip_words:
                        continue
                    
                    # Skip very short names or numbers
                    if len(name) < 3 or name.isdigit():
                        continue
                    
                    # Skip if it's just a common word
                    if name_lower in ['tab', 'cap', 'syp', 'inj', 'mg', 'ml', 'gm']:
                        continue
                    
                    found_words.add(name_lower)
                    
                    # Extract dosage from same line
                    dosage = ""
                    dosage_match = re.search(dosage_pattern, line, re.IGNORECASE)
                    if dosage_match:
                        dosage = dosage_match.group(0)
                    
                    # Extract frequency
                    frequency = ""
                    for freq_pattern in frequency_patterns:
                        freq_match = re.search(freq_pattern, line, re.IGNORECASE)
                        if freq_match:
                            frequency = freq_match.group(0)
                            break
                    
                    # Confidence based on pattern strength
                    confidence = 0.6  # Base confidence for pattern matching
                    if dosage:
                        confidence += 0.2
                    if frequency:
                        confidence += 0.1
                    
                    medicines.append(MedicineExtraction(
                        name=name,
                        dosage=dosage,
                        frequency=frequency,
                        confidence=confidence
                    ))
        
        # Remove duplicates
        unique_medicines = {}
        for med in medicines:
            key = med.name.lower()
            if key not in unique_medicines or med.confidence > unique_medicines[key].confidence:
                unique_medicines[key] = med
        
        return list(unique_medicines.values())


# Singleton instance
_vision_scanner = None

def get_vision_scanner() -> VisionScanner:
    """Get or create vision scanner instance"""
    global _vision_scanner
    if _vision_scanner is None:
        _vision_scanner = VisionScanner()
    return _vision_scanner
