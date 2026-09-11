import sys
import os

# Add parent dir to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pipeline import execute_demo_pipeline

test_cases = [
    {
        "name": "Perfect Document",
        "doc_image": b"PERFECT",
        "live_image": b"MATCHING",
        "expected_risk": "LOW"
    },
    {
        "name": "Blurry/Low-Res Image",
        "doc_image": b"BLURRY",
        "live_image": b"MATCHING",
        "expected_risk": "HIGH" # Critical pipeline errors escalate to HIGH
    },
    {
        "name": "Unsupported Doc Type",
        "doc_image": b"UNSUPPORTED",
        "live_image": b"MATCHING",
        "expected_risk": "HIGH" 
    },
    {
        "name": "Corrupted/Empty File",
        "doc_image": b"CORRUPTED",
        "live_image": b"MATCHING",
        "expected_risk": "HIGH"
    },
    {
        "name": "No Detectable Face on Doc",
        "doc_image": b"NO_FACE",
        "live_image": b"MATCHING",
        "expected_risk": "HIGH"
    },
    {
        "name": "Live Face Mismatch",
        "doc_image": b"PERFECT",
        "live_image": b"MISMATCH",
        "expected_risk": "MEDIUM" # Forces at least medium if face match is low
    },
    {
        "name": "Intentionally Broken MRZ",
        "doc_image": b"BAD_MRZ",
        "live_image": b"MATCHING",
        "expected_risk": "MEDIUM" # At least medium
    },
    {
        "name": "OCR Timeout (Hung Engine)",
        "doc_image": b"TIMEOUT_OCR",
        "live_image": b"MATCHING",
        "expected_risk": "HIGH" # Timed out, fails closed to HIGH
    },
    {
        "name": "Tamper Engine Timeout",
        "doc_image": b"TIMEOUT_TAMPER",
        "live_image": b"MATCHING",
        "expected_risk": "HIGH"
    }
]

def run_tests():
    print("| Test Case | Expected Behavior | Actual Behavior | Pass/Fail |")
    print("| :--- | :--- | :--- | :--- |")
    
    for tc in test_cases:
        try:
            res = execute_demo_pipeline(session_id="QA-100", doc_image=tc["doc_image"], live_image=tc["live_image"])
            actual_risk = res["risk_decision"]["risk_level"]
            
            # Since some expected might be "At least MEDIUM", let's handle that:
            if tc["expected_risk"] == "MEDIUM":
                passed = actual_risk in ["MEDIUM", "HIGH"]
            else:
                passed = actual_risk == tc["expected_risk"]
            
            pass_str = "PASS" if passed else "FAIL"
            explanation = res["risk_decision"]["explanation"]
            
            print(f"| {tc['name']} | Risk: {tc['expected_risk']} | Risk: {actual_risk} ({explanation}) | {pass_str} |")
        except Exception as e:
            print(f"| {tc['name']} | Risk: {tc['expected_risk']} | CRASHED: {str(e)} | FAIL (Failed Open/Crashed) |")

if __name__ == "__main__":
    run_tests()
