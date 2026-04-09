"""
Test Suite for PrescriptionValidationAgent
Verifies strict rule-based validation logic.
"""

from app.prescription_agent import PrescriptionValidationAgent
from datetime import datetime, timedelta

def test_validator():
    validator = PrescriptionValidationAgent()
    
    # Setup dates
    today = datetime.now()
    valid_date_str = today.strftime("%d-%m-%Y")
    old_date_str = (today - timedelta(days=200)).strftime("%d-%m-%Y")
    
    scenarios = [
        {
            "name": "1. VALID PRESCRIPTION",
            "text": f"Dr. Smith, MBBS. Clinic Alpha. Date: {valid_date_str}. Rx: Aspirin 100mg",
            "medicine": "Aspirin",
            "expected_valid": True
        },
        {
            "name": "2. INVALID MEDICINE (Not in text)",
            "text": f"Dr. Smith, MBBS. Date: {valid_date_str}. Rx: Ibuprofen 200mg",
            "medicine": "Aspirin",
            "expected_valid": False
        },
        {
            "name": "3. MISSING DOCTOR IDENTIFIER",
            "text": f"Date: {valid_date_str}. Rx: Aspirin 100mg. Patient: John Doe",
            "medicine": "Aspirin",
            "expected_valid": False
        },
        {
            "name": "4. OLD DATE (> 6 months)",
            "text": f"Dr. Smith, MD. Date: {old_date_str}. Rx: Aspirin 100mg",
            "medicine": "Aspirin",
            "expected_valid": False
        },
        {
            "name": "5. NO DATE FOUND",
            "text": "Dr. Smith, MBBS. Rx: Aspirin 100mg. Take twice daily.",
            "medicine": "Aspirin",
            "expected_valid": False
        }
    ]
    
    print("\n" + "="*50)
    print("RUNNING PRESCRIPTION VALIDATOR TESTS")
    print("="*50)
    
    passed_count = 0
    for s in scenarios:
        result = validator.validate(s["text"], s["medicine"])
        is_passed = result["valid"] == s["expected_valid"]
        
        status = "✅ PASS" if is_passed else "❌ FAIL"
        if is_passed: passed_count += 1
        
        print(f"\nScenario: {s['name']}")
        print(f"Result: {status} (valid={result['valid']}, confidence={result['confidence']})")
        if not result["valid"]:
            print(f"Reason: {result['reason']}")
            
    print("\n" + "="*50)
    print(f"TEST SUMMARY: {passed_count}/{len(scenarios)} PASSED")
    print("="*50 + "\n")

if __name__ == "__main__":
    test_validator()
