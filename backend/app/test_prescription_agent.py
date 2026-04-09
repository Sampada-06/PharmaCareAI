import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path to import prescription_agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prescription_agent import PrescriptionValidationAgent

def run_tests():
    agent = PrescriptionValidationAgent()
    today_str = datetime.now().strftime("%d-%m-%Y")
    
    test_cases = [
        {
            "name": "Exact Match",
            "ocr": f"Dr. Smith MBBS. Date: {today_str}. Rx: Mankind Montelukast 10mg",
            "medicine": "Mankind Montelukast 10mg",
            "expected": True
        },
        {
            "name": "Keyword Match (Molecule only)",
            "ocr": f"Dr. Gupta. Date: {today_str}. Rx: Montelukast",
            "medicine": "Mankind Montelukast 10mg",
            "expected": True
        },
        {
            "name": "Keyword Match (Partial brand)",
            "ocr": f"Dr. Clinic. Date: {today_str}. Rx: Montelukast 10 mg",
            "medicine": "Mankind Montelukast 10mg",
            "expected": True
        },
        {
            "name": "No Match",
            "ocr": f"Dr. Smith. Date: {today_str}. Rx: Paracetamol 500mg",
            "medicine": "Mankind Montelukast 10mg",
            "expected": False
        }
    ]
    
    print("\n🧪 Running Prescription Agent Keyword Match Tests...\n")
    
    passed = 0
    for i, case in enumerate(test_cases):
        result = agent.validate(case["ocr"], case["medicine"])
        is_success = result["valid"] == case["expected"]
        status = "✅ PASS" if is_success else "❌ FAIL"
        if is_success: passed += 1
        
        print(f"Test {i+1} [{case['name']}]: {status}")
        if not is_success:
            print(f"   Reason: {result['reason']}")
            
    print(f"\n📊 Result: {passed}/{len(test_cases)} tests passed.")
    return passed == len(test_cases)

if __name__ == "__main__":
    run_tests()
