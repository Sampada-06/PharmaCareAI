





















































"""
Language Detection & Translation Layer for PharmaCare AI
Detects user language, translates to English before intent extraction.
Preserves original text and medicine names. Safe for medical domain.

Uses:
  - langdetect          → language detection (fast, offline)
  - LOCAL_MEDICAL_KEYWORDS → offline Hinglish/rural keyword replacement
  - Gemini API          → translation for full Devanagari text
"""

import re
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL MEDICAL KEYWORDS — Rural / Hinglish → English
# Covers symptoms, body parts, conditions, medicine types, dosage forms,
# and common pharmacy phrases used by rural users across India.
# ═══════════════════════════════════════════════════════════════════════════════

LOCAL_MEDICAL_KEYWORDS: Dict[str, str] = {

    # ── Symptoms & Conditions ──────────────────────────────────────────────
    "bukhar":       "fever",
    "bukhaar":      "fever",
    "tez bukhar":   "high fever",
    "halka bukhar": "mild fever",
    "dard":         "pain",
    "dard ho raha": "having pain",
    "bahut dard":   "severe pain",
    "sir dard":     "headache",
    "sar dard":     "headache",
    "sardard":      "headache",
    "sir me dard":  "headache",
    "sirdard":      "headache",
    "pet dard":     "stomach ache",
    "pet me dard":  "stomach pain",
    "pet kharab":   "upset stomach",
    "kamar dard":   "back pain",
    "pith dard":    "back pain",
    "peeth dard":   "back pain",
    "ghutne ka dard":   "knee pain",
    "ghutna dard":      "knee pain",
    "jodo ka dard":     "joint pain",
    "jod dard":         "joint pain",
    "body dard":        "body pain",
    "badan dard":       "body pain",
    "seene me dard":    "chest pain",
    "chhati me dard":   "chest pain",
    "dant dard":        "toothache",
    "daant dard":       "toothache",
    "kaan dard":        "ear pain",
    "kan dard":         "ear pain",
    "aankh me dard":    "eye pain",
    "gale me dard":     "sore throat",
    "gala dard":        "sore throat",
    "gala kharab":      "sore throat",
    "bukharki goli":    "fever tablet",
    "bukhar ki goli":   "fever tablet",
    "bukharki":         "fever",
    "bukhar wali":      "fever",
    "bukharwaali":      "fever",
    "dard ki goli":     "painkiller",
    "dard wali goli":   "painkiller",
    "sar me dard":      "headache",
    "pet me mard":      "stomach pain",

    # ── Hindi/Marathi Devanagari Keywords ─────────────────────────────────
    "बुखार":           "fever",
    "बुखार है":         "having fever",
    "ताप":             "fever",
    "थंडी":            "cold",
    "सर्दी":           "cold",
    "खोकला":           "cough",
    "खोखला":           "cough",
    "सर्दी खोकला":      "cold and cough",
    "खोकला येतोय":      "having cough",
    "ताप येतोय":        "having fever",
    "दुखत":            "pain",
    "दुखत आहे":         "is hurting",
    "वेदना":           "pain",
    "वेदना होत आहेत":    "experiencing pain",
    "पोट दुखत":        "stomach pain",
    "डोकेदुखी":         "headache",
    "डोके दुखत":       "headache",
    "सर दर्द":          "headache",
    "सिर दर्द":         "headache",
    "बदन दर्द":         "body pain",
    "अंगदुखी":          "body pain",
    "कंबर":            "back pain",
    "सांधेदुखी":        "joint pain",
    "सर्दी-खोकला":      "cold and cough",
    "उलटी":           "vomiting",
    "उलट्या":          "vomiting",
    "जुलाब":           "diarrhea",
    "संडास":           "diarrhea",
    "ॲसिडिटी":         "acidity",
    "ऍसिडिटी":         "acidity",
    "जळजळ":           "acidity",
    "खरुज":           "itching",
    "खाज":            "itching",
    "सूज":             "swelling",
    "जखम":            "wound",
    "गोळी":            "tablet",
    "गोळ्या":           "tablets",
    "दवा":             "medicine",
    "औषध":            "medicine",
    "औषधे":           "medicines",
    "सिरप":           "syrup",
    "दे":              "give",
    "हवे":             "need",
    "पाहिजे":          "need",
    "pahije":          "need",
    "झाली आहे":        "have got",
    "झाला आहे":        "have got",
    "येतोय":           "is coming",
    "भरलाय":           "having",
    "दुखतय":           "hurting",
    "दुखतंय":          "hurting",
    "खूप":             "severe",
    "कमी":             "low",
    "जास्त":            "high",
    "कितीला":          "how much",
    "किंमत":           "price",
    "भाव":             "rate",
    "दाखव":            "show",
    "दाखवा":           "show",
    "पाहिजे":          "need",
    "हवी":             "need",
    "हवा":             "need",
    "तापासाठी":        "for fever",
    "तापाची गोळी":      "fever tablet",
    "सर्दीसाठी":        "for cold",
    "दुखण्यावर":        "for pain",
    "अंगदुखीसाठी":      "for body pain",
    "खोकल्यासाठी":      "for cough",
    "पोटदुखीसाठी":      "for stomach pain",
    "डोकं दुखतंय":      "headache",
    "डोकं दुखतं":       "headache",
    "डोकं":             "head",
    "पाय":              "leg",
    "हात":              "hand",
    "डोंळे":            "eyes",
    "कान":              "ear",
    "नाक":              "nose",
    "घसा":              "throat",
    "दात":              "tooth",
    "कंबर":             "back",
    "सकाळी":           "morning",
    "दुपारी":           "afternoon",
    "संध्याकाळी":        "evening",
    "रात्री":           "night",
    "जेवणानंतर":         "after meal",
    "जेवणाआधी":          "before meal",
    "कधी":              "when",
    "कसं":              "how",
    "कुठे":             "where",
    "कधी येईल":         "when will it come",
    "ऑर्डर":            "order",
    "ट्रॅक":            "track",
    "कॅन्सल":           "cancel",
    "परत":              "return",
    "पैसे":             "money",
    "किती":             "how much",

    # ── Cold, Cough, Respiratory ───────────────────────────────────────────
    "sardi":        "cold",
    "sardee":       "cold",
    "thand":        "cold",
    "jukham":       "cold",
    "nazla":        "cold",
    "khansi":       "cough",
    "khaansi":      "cough",
    "sukhi khansi": "dry cough",
    "balgam":       "phlegm",
    "balgam wali khansi": "wet cough",
    "saans":        "breathing",
    "saans phoolna":    "breathlessness",
    "saans lene me dikkat": "difficulty breathing",
    "dam":          "asthma",
    "dama":         "asthma",
    "chhink":       "sneezing",
    "naak bahna":   "runny nose",
    "naak band":    "blocked nose",
    "naak se paani": "runny nose",

    # ── Gastric, Digestive ─────────────────────────────────────────────────
    "gas":          "acidity",
    "gas banti hai":    "gas problem",
    "acidity":      "acidity",
    "khatta dakaar":    "acid reflux",
    "ulti":         "vomiting",
    "ultee":        "vomiting",
    "ji machlana":  "nausea",
    "ji ghabrana":  "nausea",
    "matli":        "nausea",
    "dast":         "diarrhea",
    "loose motion": "diarrhea",
    "pait saaf nahi": "constipation",
    "kabz":         "constipation",
    "qabz":         "constipation",
    "pet phoolna":  "bloating",
    "aafara":       "bloating",
    "pet me jalan": "stomach burning",
    "seene me jalan": "heartburn",
    "jalan":        "burning sensation",
    "achari":       "indigestion",
    "hazma kharab": "indigestion",
    "badhazmi":     "indigestion",
    "keede":        "worms",
    "pet ke keede": "stomach worms",
    "bhookh nahi lagti": "loss of appetite",

    # ── Skin & Allergy ─────────────────────────────────────────────────────
    "khujli":       "itching",
    "khaarish":     "itching",
    "daad":         "ringworm",
    "daane":        "rashes",
    "pimple":       "acne",
    "muhase":       "acne",
    "keel muhase":  "acne",
    "allergy":      "allergy",
    "chheenk":      "sneezing",
    "allergi":      "allergy",
    "jal gaya":     "burn",
    "jalana":       "burning",
    "soojan":       "swelling",
    "sooj":         "swelling",
    "sujan":        "swelling",
    "phat gayi":    "cracked skin",
    "rukhi twacha": "dry skin",
    "fungal":       "fungal infection",
    "phodi":        "boil",
    "fodi":         "boil",
    "ghav":         "wound",
    "zakhm":        "wound",
    "chot":         "injury",
    "chot lag gayi": "got injured",
    "kataana":      "cut",
    "kat gaya":     "got cut",
    "neel":         "bruise",

    # ── Fever & Infection Types ────────────────────────────────────────────
    "malaria":      "malaria",
    "dengue":       "dengue",
    "typhoid":      "typhoid",
    "viral":        "viral infection",
    "infection":    "infection",
    "infekshan":    "infection",

    # ── Diabetes & BP ──────────────────────────────────────────────────────
    "sugar":        "diabetes",
    "sugar ki bimari":  "diabetes",
    "madhumeh":     "diabetes",
    "bp":           "blood pressure",
    "bp badha hua": "high blood pressure",
    "bp kam":       "low blood pressure",
    "uchh raktchap":    "high blood pressure",

    # ── Eyes & ENT ─────────────────────────────────────────────────────────
    "aankh lal":    "eye redness",
    "aankh me jalan":   "eye irritation",
    "aankh se paani":   "watery eyes",
    "nazar kamzor": "weak eyesight",
    "kaan me awaaz":    "ear ringing",
    "kaan behna":   "ear discharge",

    # ── Women's & General Health ───────────────────────────────────────────
    "mahawari":     "menstruation",
    "mahawari dard":    "period pain",
    "period dard":  "period pain",
    "periods me dard":  "menstrual cramp",
    "pet me marod":     "stomach cramps",
    "kamzori":      "weakness",
    "kamjori":      "weakness",
    "thakan":       "fatigue",
    "chakkar":      "dizziness",
    "chakkar aana": "feeling dizzy",
    "behoshi":      "fainting",
    "neend nahi aati":  "insomnia",
    "neend ki dawai":   "sleeping medicine",
    "nind nahi aati":   "insomnia",
    "tension":      "anxiety",
    "ghabrahat":    "anxiety",
    "khoon ki kami":    "anemia",
    "khoon kam":    "anemia",
    "peshab me jalan":  "urinary burning",
    "baar baar peshab": "frequent urination",
    "peshab ruk ruk ke": "urine retention",
    "bawaseer":     "piles",
    "bawasir":      "piles",
    "piliya":       "jaundice",

    # ── Children & Common ──────────────────────────────────────────────────
    "bachhe ko bukhar": "child has fever",
    "bacche ka dast":   "child has diarrhea",
    "khana hazam nahi": "indigestion",
    "muh me chhale":    "mouth ulcers",
    "chhale":       "ulcers",
    "tonsil":       "tonsillitis",

    # ── Medicine Types (rural descriptions) ────────────────────────────────
    "goli":         "tablet",
    "goliyan":      "tablets",
    "dawai":        "medicine",
    "dawa":         "medicine",
    "davai":        "medicine",
    "dawaai":       "medicine",
    "syrup":        "syrup",
    "chaashni":     "syrup",
    "cream":        "cream",
    "malham":       "ointment",
    "marham":       "ointment",
    "patti":        "bandage",
    "injection":    "injection",
    "sui":          "injection",
    "drip":         "IV drip",
    "drop":         "drops",
    "tel":          "oil",
    "churan":       "powder",
    "chooran":      "digestive powder",
    "pudia":        "sachet",
    "pudiya":       "sachet",
    "capsule":      "capsule",
    "tonic":        "tonic",
    "balm":         "balm",

    # ── Pharmacy Phrases ───────────────────────────────────────────────────
    "dawai do":         "give medicine",
    "dawai chahiye":    "need medicine",
    "dawai de do":      "give medicine",
    "dawa do":          "give medicine",
    "kya hai":          "is available",
    "milegi":           "will I get",
    "mil jayegi":       "will I get",
    "hai kya":          "is it available",
    "kitne ka hai":     "what is the price",
    "kitne ki hai":     "what is the price",
    "kya rate hai":     "what is the price",
    "kitna paisa":      "how much cost",
    "likh do":          "prescribe",
    "dikhao":           "show me",
    "dikha do":         "show me",
    "chahiye":          "need",
    "chaahiye":         "need",
    "de do":            "give",
    "dedo":             "give",
    "bhejo":            "send",
    "mangwao":          "order",
    "order karo":       "place order",
    "order kar do":     "place order",
    "cancel karo":      "cancel order",
    "kaha tak aaya":    "where is my order",
    "kab milega":       "when will I get",
    "kab aayega":       "when will it arrive",
    "jhali aahe":       "have got",
    "jhala aahe":       "have got",
    "yetoy":            "coming",
    "bhartay":          "having",
    "dukhatay":         "hurting",
    "dukhata":          "hurting",
    "khoop":            "severe",
    "khup":             "severe",
    "kami":             "low",
    "jasta":            "high",
    "jast":             "high",
    "tapasathi goli":   "fever tablet",
    "taapsathi goli":   "fever tablet",
    "taapasathi":       "for fever",
    "tapasathi":        "for fever",
    "tapasachi goli":   "fever tablet",
    "sardisathi":       "for cold",
    "khoklyasathi":     "for cough",
    "potdukhisathi":    "for stomach pain",
    "dokasathi":        "for head",
    "angdukhisathi":    "for body pain",
    "goli ki goli":     "tablet",
    "mala":             "for me",
    "majha":            "my",
    "aamche":           "our",
    "tumcha":           "your",
    "daakhva":          "show",
    "dakhav":           "show",
    "daakhva":          "show",

    # ── Medicine Names (transliterated) ────────────────────────────────────
    "parasiṭamol":  "Paracetamol",
    "parasetamol":  "Paracetamol",
    "parasitamol":  "Paracetamol",
    "paracetamol":  "Paracetamol",
    "crocin":       "Crocin",
    "krosin":       "Crocin",
    "dolo":         "Dolo",
    "combiflam":    "Combiflam",
    "ibuprofen":    "Ibuprofen",
    "aspirin":      "Aspirin",
    "cetrizine":    "Cetirizine",
    "cetirizine":   "Cetirizine",
    "setirijin":    "Cetirizine",
    "metformin":    "Metformin",
    "metfaarmin":   "Metformin",
    "amoxicillin":  "Amoxicillin",
    "azithromycin": "Azithromycin",
    "omeprazole":   "Omeprazole",
    "pantoprazol":  "Pantoprazole",
    "pan d":        "Pan D",
    "gelusil":      "Gelusil",
    "digene":       "Digene",
    "eno":          "Eno",
    "hajmola":      "Hajmola",
    "pudin hara":   "Pudin Hara",
    "vicks":        "Vicks",
    "benadryl":     "Benadryl",
    "benidryl":     "Benadryl",
    "oars":         "ORS",
    "ors":          "ORS",
    "electral":     "Electral",
    "betadine":     "Betadine",
    "dettol":       "Dettol",
    "savlon":       "Savlon",
    "band aid":     "Band-Aid",
    "bandaid":      "Band-Aid",
    "moov":         "Moov",
    "volini":       "Volini",
    "zandu balm":   "Zandu Balm",
    "amrutanjan":   "Amrutanjan",
    "disprin":      "Disprin",
    "saridon":      "Saridon",
    "sinarest":     "Sinarest",
    "strepsils":    "Strepsils",
    "limcee":       "Limcee",
    "becosule":     "Becosule",
    "shelcal":      "Shelcal",
    "revital":      "Revital",
    "montair":      "Montair",
    "allegra":      "Allegra",
    "calamine":     "Calamine",
    "burnol":       "Burnol",
    "boroline":     "Boroline",
    "amlodipine":   "Amlodipine",
    "losartan":     "Losartan",
    "atenolol":     "Atenolol",
    "ranitidine":   "Ranitidine",
    "domperidone":  "Domperidone",
    "ondansetron":  "Ondansetron",
    "loperamide":   "Loperamide",
    "norfloxacin":  "Norfloxacin",
    "ciprofloxacin":"Ciprofloxacin",
    "ofloxacin":    "Ofloxacin",

    # ── Body Parts ─────────────────────────────────────────────────────────
    "sir":      "head",
    "sar":      "head",
    "pet":      "stomach",
    "pait":     "stomach",
    "kamar":    "back",
    "pith":     "back",
    "peeth":    "back",
    "haath":    "hand",
    "pair":     "leg",
    "ghutna":   "knee",
    "aankh":    "eye",
    "naak":     "nose",
    "kaan":     "ear",
    "gala":     "throat",
    "dant":     "tooth",
    "daant":    "tooth",
    "seena":    "chest",
    "chhati":   "chest",
    "ungli":    "finger",
    "twacha":   "skin",
    "chamdi":   "skin",
}


# ── Medical / Brand tokens that must NEVER be translated ──────────────────────
_BRAND_PATTERN = re.compile(
    r'\b\d+\s*(?:mg|ml|mcg|iu|gm?|kg|%)\b'   # dosage patterns: 500mg, 10ml
    r'|'
    r'\b(?:XR|SR|CR|ER|DR|MR|XL|DS|Plus|Forte|Max|Ultra|Pro|Duo)\b',
    re.IGNORECASE,
)

# Pattern to detect if a string is primarily numeric / dosage
_NUMERIC_HEAVY = re.compile(r'^[\d\s\.\,\-\+mg%mliu]+$', re.IGNORECASE)

# Cached Gemini model for translation (lazy init)
_translation_model = None


def _get_translation_model():
    """Lazily initialize a Gemini model for translation."""
    global _translation_model
    if _translation_model is not None:
        return _translation_model

    try:
        import google.generativeai as genai
        # Try both env locations for reliability
        api_key = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'").strip()
        if not api_key:
            # Fallback for some environments
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'").strip()
            
        if api_key:
            genai.configure(api_key=api_key)
            _translation_model = genai.GenerativeModel('gemini-2.0-flash')
            return _translation_model
    except Exception as e:
        logger.warning(f"Failed to init Gemini for translation: {e}")

    return None


def _is_brand_heavy(text: str) -> bool:
    """Return True if the text is mostly brand tokens / dosage info."""
    tokens = text.split()
    if not tokens:
        return False
    brand_count = sum(1 for t in tokens if _BRAND_PATTERN.search(t))
    return brand_count / len(tokens) > 0.5


def _apply_local_keywords(text: str) -> tuple[str, bool]:
    """
    Replace Hinglish / romanized Hindi medical terms with English equivalents.
    Works OFFLINE — no API call needed.

    Returns:
        (processed_text, was_modified)
    """
    lower = text.lower()
    modified = False

    # Sort keywords by length (longest first) to avoid partial matches
    sorted_keywords = sorted(LOCAL_MEDICAL_KEYWORDS.keys(), key=len, reverse=True)

    for keyword in sorted_keywords:
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
        if pattern.search(lower):
            replacement = LOCAL_MEDICAL_KEYWORDS[keyword]
            text = pattern.sub(replacement, text)
            lower = text.lower()
            modified = True

    return text.strip(), modified


def _detect_language(text: str) -> str:
    """Detect language with robust handling for medical/English text."""
    # 1. Quick Devanagari check (Hindi/Marathi)
    if any("\u0900" <= char <= "\u097f" for char in text):
        try:
            from langdetect import detect
            lang = detect(text)
            return lang if lang in ['hi', 'mr'] else 'hi'
        except:
            return 'hi'
    
    # 2. English/Medical check
    if _NUMERIC_HEAVY.match(text) or _is_brand_heavy(text):
        return "en"
    
    # ── Romanized Language Check ───────────────────────────────────────
    # We check if certain keywords are present to suggest it's more likely HI or MR
    # even if written in Roman script.
    mr_roman_keywords = {'pahije', 'dakhav', 'mala', 'mazya', 'tapasathi', 'taapasathi', 'tappasathi', 'taap'}
    hi_roman_keywords = {'chahiye', 'dikhao', 'mujhe', 'mere', 'bukhar', 'bukhaar', 'chahie'}
    words = set(text.lower().split())
    
    if words.intersection(mr_roman_keywords): return "mr"
    if words.intersection(hi_roman_keywords): return "hi"

    # Common English pharmacy words
    common_en = {'add', 'to', 'cart', 'order', 'please', 'medicine', 'show', 'view', 'clear', 'search', 'buy', 'track'}
    if words.intersection(common_en) or text.isascii():
        return "en"

    # 3. Fallback to langdetect with whitelist
    try:
        from langdetect import detect, DetectorFactory
        DetectorFactory.seed = 0
        lang = detect(text)
        if lang in ['hi', 'mr', 'en']:
            return lang
        return "en"
    except Exception as e:
        logger.warning(f"Language detection failed: {e}. Defaulting to 'en'.")
        return "en"


def _translate_to_english(text: str, src_lang: str) -> str:
    """
    Translate text to English using Gemini API.
    Preserves brand tokens and dosage information.
    Falls back to original text on any error.
    """
    # 1. Try Gemini (Primary)
    try:
        model = _get_translation_model()
        if model:
            # Build a safe, constrained prompt for medical translation
            prompt = f"""Translate the following text to English.
RULES:
- Do NOT change any medicine names, brand names or dosages
- Do NOT change any numbers or quantities
- Do NOT add or remove information
- Return ONLY the translated text, nothing else

Text: {text}"""

            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 200,
                    "temperature": 0.1,
                }
            )

            if response and response.text:
                translated = response.text.strip()
                # Remove any markdown formatting that Gemini might add
                if translated.startswith('"') and translated.endswith('"'):
                    translated = translated[1:-1]
                translated = ' '.join(translated.split())
                return translated
    except Exception as e:
        logger.warning(f"Gemini translation failed: {e}")

    # 2. Try Groq (Fast & Reliable Fallback)
    try:
        api_key = os.getenv("GROQ_API_KEY", "").strip('"').strip("'").strip()
        if api_key:
            from groq import Groq
            client = Groq(api_key=api_key)
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Translate the text to English. Return ONLY the translated text. DO NOT change medicine names, brand names, or dosages."},
                    {"role": "user", "content": text}
                ],
                max_tokens=200,
                temperature=0.1,
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq translation failed: {e}")

    return text


def process_user_input(text: str) -> dict:
    """
    Main entry point for the language processing layer.

    Pipeline:
        1. Apply LOCAL_MEDICAL_KEYWORDS (offline, instant)
        2. Detect language
        3. If non-English → translate via Gemini
        4. Return result with original text preserved

    Args:
        text: Raw user input string.

    Returns:
        dict with keys:
            - original_text: str (unchanged user input)
            - detected_language: str (ISO 639-1 code)
            - translated_text: str (English translation or original if already English)
    """
    original_text = text.strip()

    # Guard: empty input
    if not original_text:
        result = {
            "original_text": "",
            "detected_language": "en",
            "translated_text": "",
        }
        _log_event(result)
        return result

    # Guard: numeric-heavy / brand-heavy strings — skip translation entirely
    if _NUMERIC_HEAVY.match(original_text) or _is_brand_heavy(original_text):
        result = {
            "original_text": original_text,
            "detected_language": "en",
            "translated_text": original_text,
        }
        _log_event(result)
        return result

    # ── Step 1: Apply local keyword replacement (handles Hinglish) ─────
    keyword_processed, had_local_keywords = _apply_local_keywords(original_text)

    # ── Step 2: Detect language ────────────────────────────────────────
    detected_language = _detect_language(original_text)

    # ── Step 3: Decide translation strategy ────────────────────────────
    if detected_language == "en":
        # English text — but might be Hinglish that langdetect thinks is English
        # If local keywords were found, use the keyword-replaced version
        translated_text = keyword_processed if had_local_keywords else original_text
    else:
        # Non-English (Devanagari etc.) — use Gemini for full translation
        translated_text = _translate_to_english(original_text, detected_language)
        # Also apply local keywords on the Gemini output for any missed terms
        translated_text, _ = _apply_local_keywords(translated_text)

    result = {
        "original_text": original_text,
        "detected_language": detected_language,
        "translated_text": translated_text,
    }

    _log_event(result)
    return result


def _log_event(result: dict) -> None:
    """Emit structured log for observability."""
    logger.info(
        "language_processing",
        extra={
            "event": "language_processing",
            "original_text": result["original_text"],
            "detected_language": result["detected_language"],
            "translated_text": result["translated_text"],
        }
    )
    # Also print for console visibility during development
    if result["detected_language"] != "en" or result["original_text"] != result["translated_text"]:
        safe_orig = result['original_text'][:60].encode('ascii', 'replace').decode('ascii')
        safe_trans = result['translated_text'][:60].encode('ascii', 'replace').decode('ascii')
        print(
            f"Language: {result['detected_language']} | "
            f"Original: {safe_orig} | "
            f"Translated: {safe_trans}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SYMPTOM → MEDICINE SEARCH TERMS
# Maps symptom/condition keywords to actual medicine names for inventory search.
# When a user says "fever ki goli" we should search for Paracetamol, Crocin etc.
# ═══════════════════════════════════════════════════════════════════════════════

SYMPTOM_TO_SEARCH_TERMS: Dict[str, list] = {
    # Fever & Pain
    "fever":            ["Paracetamol", "Crocin", "Dolo", "Calpol"],
    "high fever":       ["Paracetamol", "Crocin", "Dolo"],
    "mild fever":       ["Paracetamol", "Crocin"],
    "pain":             ["Paracetamol", "Ibuprofen", "Combiflam", "Diclofenac"],
    "severe pain":      ["Combiflam", "Diclofenac", "Ibuprofen"],
    "headache":         ["Paracetamol", "Saridon", "Disprin", "Crocin"],
    "body pain":        ["Combiflam", "Ibuprofen", "Diclofenac"],
    "back pain":        ["Combiflam", "Diclofenac", "Moov", "Volini"],
    "knee pain":        ["Diclofenac", "Combiflam", "Volini"],
    "joint pain":       ["Diclofenac", "Combiflam", "Volini"],
    "toothache":        ["Combiflam", "Ibuprofen", "Diclofenac"],
    "stomach ache":     ["Cyclopam", "Meftal", "Buscopan"],
    "stomach pain":     ["Cyclopam", "Meftal", "Buscopan"],
    "stomach cramps":   ["Cyclopam", "Meftal", "Buscopan"],
    "ear pain":         ["Paracetamol", "Otrivin"],
    "eye pain":         ["Paracetamol"],
    "sore throat":      ["Strepsils", "Betadine Gargle", "Paracetamol"],
    "chest pain":       ["Sorbitrate", "Aspirin"],

    # Cold & Cough
    "cold":             ["Sinarest", "Cetirizine", "Vicks", "Crocin Cold"],
    "cough":            ["Benadryl", "Honitus", "Ascoril", "Grilinctus"],
    "dry cough":        ["Benadryl", "Honitus"],
    "wet cough":        ["Ascoril", "Grilinctus", "Ambroxol"],
    "phlegm":           ["Ambroxol", "Ascoril", "Mucinex"],
    "sneezing":         ["Cetirizine", "Allegra", "Sinarest"],
    "runny nose":       ["Cetirizine", "Sinarest", "Otrivin Nasal"],
    "blocked nose":     ["Otrivin", "Sinarest", "Nasivion"],

    # Breathing
    "breathlessness":   ["Deriphyllin", "Salbutamol", "Asthalin"],
    "asthma":           ["Asthalin", "Deriphyllin", "Montair"],
    "difficulty breathing": ["Deriphyllin", "Salbutamol"],

    # Gastric & Digestive
    "acidity":          ["Gelusil", "Digene", "Eno", "Pantoprazole", "Omeprazole"],
    "gas problem":      ["Gelusil", "Digene", "Eno", "Gas-O-Fast"],
    "acid reflux":      ["Pantoprazole", "Omeprazole", "Ranitidine"],
    "vomiting":         ["Ondansetron", "Domperidone", "Emeset"],
    "nausea":           ["Ondansetron", "Domperidone"],
    "diarrhea":         ["ORS", "Loperamide", "Norfloxacin", "Electral"],
    "constipation":     ["Dulcolax", "Isabgol", "Cremaffin", "Lactulose"],
    "bloating":         ["Gelusil", "Digene", "Gas-O-Fast", "Pudina"],
    "heartburn":        ["Pantoprazole", "Omeprazole", "Eno"],
    "burning sensation":["Pantoprazole", "Gelusil"],
    "indigestion":      ["Hajmola", "Pudin Hara", "Digene", "Gelusil"],
    "stomach burning":  ["Pantoprazole", "Omeprazole", "Gelusil"],
    "stomach worms":    ["Albendazole", "Zentel", "Mebendazole"],
    "worms":            ["Albendazole", "Zentel"],
    "loss of appetite": ["Liv 52", "Aptivate"],

    # Skin & Allergy
    "itching":          ["Cetirizine", "Calamine", "Betnovate"],
    "ringworm":         ["Clotrimazole", "Ring Guard", "Candid"],
    "rashes":           ["Calamine", "Cetirizine", "Betnovate"],
    "acne":             ["Benzoyl Peroxide", "Clindamycin"],
    "allergy":          ["Cetirizine", "Allegra", "Montair"],
    "burn":             ["Burnol", "Silver Sulfadiazine"],
    "swelling":         ["Combiflam", "Diclofenac", "Ibuprofen"],
    "cracked skin":     ["Boroline", "Vaseline"],
    "dry skin":         ["Boroline", "Moisturizer"],
    "fungal infection": ["Clotrimazole", "Candid", "Fluconazole"],
    "boil":             ["Magnesium Sulphate", "Betadine"],
    "wound":            ["Betadine", "Povidone Iodine", "Soframycin"],
    "injury":           ["Betadine", "Diclofenac", "Crepe Bandage"],
    "cut":              ["Betadine", "Band-Aid", "Dettol"],
    "bruise":           ["Thrombophob", "Heparinoid"],

    # Infection
    "viral infection":  ["Paracetamol", "Cetirizine", "Crocin"],
    "infection":        ["Amoxicillin", "Azithromycin", "Ciprofloxacin"],
    "malaria":          ["Chloroquine", "Artemether"],
    "typhoid":          ["Ciprofloxacin", "Cefixime"],

    # Diabetes & BP
    "diabetes":         ["Metformin", "Glimepiride"],
    "blood pressure":   ["Amlodipine", "Losartan", "Atenolol"],
    "high blood pressure": ["Amlodipine", "Losartan", "Telmisartan"],
    "low blood pressure":  ["ORS", "Electral"],

    # Eyes & ENT
    "eye redness":      ["Naphazoline Eye Drops"],
    "eye irritation":   ["Refresh Tears", "Itone"],
    "watery eyes":      ["Naphazoline", "Cetirizine"],
    "ear discharge":    ["Ciprofloxacin Ear Drops"],

    # Women's Health
    "period pain":       ["Meftal Spas", "Ibuprofen", "Cyclopam"],
    "menstrual cramp":   ["Meftal Spas", "Cyclopam"],

    # General
    "weakness":         ["Becosule", "Revital", "Supradyn", "Zincovit"],
    "fatigue":          ["Revital", "Supradyn", "Becosule"],
    "dizziness":        ["Stemetil", "ORS"],
    "fainting":         ["ORS", "Electral"],
    "insomnia":         ["Melatonin"],
    "sleeping medicine":["Melatonin"],
    "anxiety":          ["Calm Aid"],
    "anemia":           ["Ferrous Sulphate", "Folic Acid", "Autrin"],
    "urinary burning":  ["Norfloxacin", "Cystone"],
    "frequent urination":["Cystone"],
    "piles":            ["Anusol", "Proctosedyl"],
    "jaundice":         ["Liv 52", "Ursodeoxycholic Acid"],
    "child has fever":  ["Calpol", "Paracetamol Syrup"],
    "child has diarrhea":["ORS", "Electral"],
    "mouth ulcers":     ["Smyle Gel", "Triamcinolone"],
    "tonsillitis":      ["Amoxicillin", "Paracetamol"],
}


def get_medicine_search_terms(text: str) -> list:
    """
    Extract actual medicine search terms from symptom-based queries.
    
    Given translated text like "fever tablet need", this checks for symptom 
    keywords and returns actual medicine names to search in inventory.
    
    Args:
        text: The translated/processed user text (English).
    
    Returns:
        List of medicine names to search for, or empty list if no symptoms found.
    """
    text_lower = text.lower()
    search_terms = []
    
    # Sort by length (longest first) to match multi-word symptoms like "high fever" before "fever"
    sorted_symptoms = sorted(SYMPTOM_TO_SEARCH_TERMS.keys(), key=len, reverse=True)
    
    for symptom in sorted_symptoms:
        if symptom in text_lower:
            search_terms.extend(SYMPTOM_TO_SEARCH_TERMS[symptom])
            # Remove matched symptom to avoid double-matching
            text_lower = text_lower.replace(symptom, "")
    
    # Deduplicate while preserving order
    seen = set()
    unique_terms = []
    for term in search_terms:
        if term not in seen:
            seen.add(term)
            unique_terms.append(term)
    
    return unique_terms
