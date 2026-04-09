"""
Medicine Name Matcher — Fuzzy Search & Transliteration
Matches user input against Supabase pharmacy_products table.
Uses rapidfuzz for typo-tolerant matching.
"""

import os
import logging
from rapidfuzz import process, fuzz
from app.supabase_client import supabase

logger = logging.getLogger(__name__)

_product_names_cache: list[str] = []
FUZZY_THRESHOLD = 70.0

def _load_product_names() -> list[str]:
    """Load product names from Supabase."""
    global _product_names_cache
    
    if not supabase:
        return _product_names_cache

    try:
        response = supabase.table("pharmacy_products").select("product_name").execute()
        _product_names_cache = [m["product_name"] for m in response.data if m.get("product_name")]
        logger.info(f"Loaded {len(_product_names_cache)} medicine names from Supabase")
    except Exception as e:
        logger.error(f"Failed to load medicine names from Supabase: {e}")
        
    return _product_names_cache

# ── Transliteration Map (Hindi / Marathi → English) ────────────────────────
TRANSLITERATION_MAP: dict[str, str] = {
    # Common drugs
    "पेरासिटामोल": "Paracetamol",
    "एस्पिरिन": "Aspirin",
    "क्रोसिन": "Crocin",
    "डिस्प्रिन": "Disprin",
    "इबुप्रोफेन": "Ibuprofen",
    "अमोक्सिसिलिन": "Amoxicillin",
    "सेट्रिजिन": "Cetirizine",
    "मेटफॉर्मिन": "Metformin",
    "अज़िथ्रोमाइसिन": "Azithromycin",
    "विक्स": "Vicks",
    "कॉम्बीफ्लैम": "Combiflam",
    "बिकासुल": "Becosules",
    "parasetamol": "Paracetamol",
    "parasitamol": "Paracetamol",
    "parasiṭamol": "Paracetamol",
}

# ── Core matching function ──────────────────────────────────────────────────

def match_medicine_name(user_input: str) -> dict:
    """
    Match user input to a medicine in the Supabase database.
    """
    product_names = _load_product_names()

    if not product_names or not user_input:
        _log_result(user_input, "", 0.0)
        return {"matched_name": "", "confidence": 0.0}

    # 1. Normalize
    normalized = user_input.strip().lower()

    # 2. Transliteration lookup
    if normalized in TRANSLITERATION_MAP:
        translated = TRANSLITERATION_MAP[normalized]
        logger.info(f"Transliteration: '{normalized}' → '{translated}'")
        normalized = translated.lower()

    # 3. Exact substring match (case-insensitive)
    for name in product_names:
        if normalized in name.lower():
            _log_result(user_input, name, 100.0)
            return {"matched_name": name, "confidence": 100.0}

    # 4. Fuzzy match
    result = process.extractOne(
        normalized,
        product_names,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=FUZZY_THRESHOLD,
    )

    if result is not None:
        matched_name, score, _ = result
        _log_result(user_input, matched_name, round(score, 2))
        return {"matched_name": matched_name, "confidence": round(score, 2)}

    # 5. No match
    _log_result(user_input, "", 0.0)
    return {"matched_name": "", "confidence": 0.0}


def _log_result(user_input: str, matched_name: str, confidence: float) -> None:
    """Structured log for every match attempt."""
    logger.info(
        "medicine_match | input=%s | matched_name=%s | confidence=%.2f",
        user_input,
        matched_name or "(none)",
        confidence,
    )
