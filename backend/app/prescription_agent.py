"""
Strict Rule-Based Prescription Validation Agent
Deterministic logic for medical-grade validation.
No LLM usage. No AI interpretation.
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

class PrescriptionValidationAgent:
    """
    Agent for medical-grade prescription validation using deterministic rules.
    """

    def __init__(self):
        # Doctor identifiers required for Rule 2
        self.doc_identifiers = ["dr.", "mbbs", "md", "bams", "clinic"]
        # Max age of prescription in days for Rule 4
        self.max_age_days = 180

    def extract_dates(self, text: str) -> List[datetime]:
        """
        Finds and parses dates from text using multiple regex patterns.
        DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD
        """
        # Patterns for DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD
        patterns = [
            r'(\d{2})[-/](\d{2})[-/](\d{4})',  # DD-MM-YYYY or DD/MM/YYYY
            r'(\d{4})[-/](\d{2})[-/](\d{2})'   # YYYY-MM-DD
        ]
        
        found_dates = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                date_str = match.group(0)
                try:
                    # Try DD-MM-YYYY or DD/MM/YYYY
                    if '-' in date_str or '/' in date_str:
                        if pattern == patterns[0]:
                            # Distinguish between DD-MM-YYYY and others if needed
                            sep = '-' if '-' in date_str else '/'
                            dt = datetime.strptime(date_str, f"%d{sep}%m{sep}%Y")
                        else:
                            sep = '-' if '-' in date_str else '/'
                            dt = datetime.strptime(date_str, f"%Y{sep}%m{sep}%d")
                        found_dates.append(dt)
                except ValueError:
                    continue  # Safely ignore invalid dates (e.g. 32-13-2024)

        return found_dates

    def validate(self, ocr_text: str, medicine_name: str) -> Dict[str, Any]:
        """
        Validates OCR text against 4 strict rules.
        """
        # Normalize text
        normalized_text = ocr_text.lower().strip()
        search_medicine = (medicine_name or "").lower().strip()

        # RULE 1: Medicine Match (Keyword-based)
        # 1. Clean medicine name: remove dosage units and generic terms
        clean_search = re.sub(r'\d+(?:\.\d+)?\s*(?:mg|ml|mcg|g|tabs?|caps?)', '', search_medicine)
        noise_words = {"mg", "ml", "tablet", "tablets", "capsule", "capsules", "syrup", "suspension", "x", "qty", "dose"}
        keywords = [k for k in clean_search.split() if k and k not in noise_words and len(k) > 2]
        
        # If no keywords left after cleaning, fallback to original split
        if not keywords:
            keywords = [k for k in search_medicine.split() if k and k not in noise_words and len(k) > 2]

        # 2. Check if at least one significant keyword matches
        found_keywords = [k for k in keywords if k in normalized_text]
        
        # We require at least one match for Rule 1 to pass
        if not found_keywords:
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": f"Medicine keywords '{', '.join(keywords)}' (from '{medicine_name}') not found in prescription text.",
                "latest_date": None
            }

        # Confidence boost if multiple keywords found
        match_confidence = 0.5 + (0.4 * (len(found_keywords) / len(keywords))) if keywords else 0.5

        # RULE 2: Doctor Identifier
        has_doc = any(ident in normalized_text for ident in self.doc_identifiers)
        if not has_doc:
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": "Missing doctor identifier (Dr., MBBS, MD, BAMS, or Clinic).",
                "latest_date": None
            }

        # RULE 3: Valid Date Exists
        dates = self.extract_dates(normalized_text)
        if not dates:
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": "No valid prescription date found (Expected formats: DD-MM-YYYY, YYYY-MM-DD).",
                "latest_date": None
            }

        # RULE 4: Date Recency Check
        latest_date = max(dates)
        today = datetime.now()
        age = today - latest_date

        if age.days > self.max_age_days:
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": f"Prescription is too old ({age.days} days ago). Maximum allowed is 180 days.",
                "latest_date": latest_date.strftime("%Y-%m-%d")
            }
        
        if age.days < -1: # Allow some buffer for timezone/clock drift (1 day)
            return {
                "valid": False,
                "confidence": 0.0,
                "reason": f"Prescription date {latest_date.strftime('%Y-%m-%d')} is in the future.",
                "latest_date": latest_date.strftime("%Y-%m-%d")
            }

        # CONFIDENCE LOGIC: All rules pass
        return {
            "valid": True,
            "confidence": 0.95,
            "reason": "Prescription passed all rule-based validation checks.",
            "latest_date": latest_date.strftime("%Y-%m-%d")
        }
