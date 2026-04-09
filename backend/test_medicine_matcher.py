"""
Test script for medicine_matcher.py
Validates exact, fuzzy, transliteration, and no-match cases.
"""

import sys
import os
import logging

# Ensure app module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

from app.medicine_matcher import match_medicine_name

# ── Test cases ──────────────────────────────────────────────────────────────

TEST_CASES = [
    # (input, description, expect_match, min_confidence)
    ("Paracetamol",       "Exact match",                True,  100),
    ("Cetirizine 10mg",   "Exact match with dosage",    True,  100),
    ("Omega 3",           "Partial match",              True,   80),
    ("Paracitamol",       "Misspelling (translitmap)",  True,   80),
    ("Cetirzine",         "Misspelling (translitmap)",  True,   80),
    ("ibuprofin",         "Misspelling (translitmap)",  True,   80),
    ("bukhar ki goli",    "Hindi transliteration",      True,   80),
    ("dard ki dawa",      "Hindi transliteration",      True,   80),
    ("gas ki dawa",       "Hindi transliteration",      True,   80),
    ("allergy ki goli",   "Hindi transliteration",      True,   80),
    ("sugar ki dawa",     "Hindi transliteration",      True,   80),
    ("XYZABC123",         "No match (garbage input)",   False,   0),
    ("asdfghjklqwert",    "No match (random string)",   False,   0),
]

PASS = 0
FAIL = 0

print("=" * 75)
print("MEDICINE MATCHER — TEST RESULTS")
print("=" * 75)

for user_input, description, expect_match, min_conf in TEST_CASES:
    result = match_medicine_name(user_input)
    matched = bool(result["matched_name"])
    confidence = result["confidence"]

    ok = (matched == expect_match) and (confidence >= min_conf if expect_match else confidence == 0)

    status = "✅ PASS" if ok else "❌ FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1

    print(f"\n{status} | {description}")
    print(f"  Input:      \"{user_input}\"")
    print(f"  Matched:    \"{result['matched_name']}\"")
    print(f"  Confidence: {confidence}")
    if not ok:
        print(f"  Expected:   match={expect_match}, min_conf={min_conf}")

print("\n" + "=" * 75)
print(f"TOTAL: {PASS + FAIL} | PASSED: {PASS} | FAILED: {FAIL}")
print("=" * 75)

sys.exit(0 if FAIL == 0 else 1)
