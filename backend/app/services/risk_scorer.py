from typing import Tuple, Dict, Any, List

from app.core.config import settings

class RiskThresholds:
    """Configurable thresholds for risk scoring."""
    FACE_MATCH_MIN = settings.THRESHOLD_FACE_MATCH
    TAMPER_MAX = settings.THRESHOLD_TAMPER
    TAMPER_EXTREME = settings.THRESHOLD_TAMPER_EXTREME
    METADATA_ANOMALY_MAX = settings.THRESHOLD_METADATA

def calculate_risk_score(
    mrz_status: str,
    tampering_status: str,
    tamper_score: float,
    face_status: str,
    face_match_score: float,
    pipeline_errors: List[str],
    thresholds: RiskThresholds = RiskThresholds()
) -> Dict[str, Any]:
    """
    Fuses multiple signals into a single LOW/MEDIUM/HIGH/REVIEW_REQUIRED risk label.
    Distinguishes between verified fraud indicators and missing dependencies.
    """
    
    fraud_reasons: List[str] = []
    offline_reasons: List[str] = []
    
    risk_level = "LOW"
    
    # --- 1. Fraud Detection Checks (Forces MEDIUM or HIGH) ---
    
    # A. MRZ Analysis
    if mrz_status == "MRZ_INVALID":
        fraud_reasons.append("MRZ checksum invalid")
        risk_level = "MEDIUM"
        
    # B. Tampering Analysis
    if tampering_status == "TAMPERING_DETECTED" or (tampering_status == "NO_TAMPERING_INDICATOR" and tamper_score > thresholds.TAMPER_MAX):
        fraud_reasons.append(f"Tampering detected (confidence: {int(tamper_score * 100)}%)")
        risk_level = "MEDIUM"
        
    # C. Face Analysis
    if face_status == "FACE_NO_MATCH" or (face_status == "FACE_MATCH" and face_match_score < thresholds.FACE_MATCH_MIN):
         fraud_reasons.append(f"Face mismatch (similarity: {int(face_match_score * 100)}%)")
         risk_level = "MEDIUM"
         
    # --- 2. Graceful Fallbacks for Missing Dependencies ---
    
    if mrz_status in ["OCR_UNAVAILABLE", "MRZ_ERROR"]:
        offline_reasons.append("OCR/MRZ unavailable")
        
    if tampering_status in ["ANALYSIS_UNAVAILABLE", "INVALID_IMAGE"]:
        offline_reasons.append(f"Tamper analysis failed: {tampering_status}")
        
    if face_status in ["FACE_ANALYSIS_UNAVAILABLE", "FACE_NOT_FOUND", "FACE_INCONCLUSIVE", "INVALID_IMAGE"]:
        offline_reasons.append(f"Face analysis inconclusive: {face_status}")
        
    if pipeline_errors:
        offline_reasons.append(f"System errors: {len(pipeline_errors)} detected")
        
    # --- 3. Risk Escalation Rules ---
    
    # If ANY fraud is detected, it overrides REVIEW_REQUIRED and sets to HIGH if there are multiple triggers.
    if fraud_reasons:
        if len(fraud_reasons) >= 2 or tamper_score > thresholds.TAMPER_EXTREME:
            risk_level = "HIGH"
    elif offline_reasons:
        # No actual fraud detected, but we lack complete evidence.
        risk_level = "REVIEW_REQUIRED"
        
    # --- 4. Explanation Generation ---
    
    if risk_level == "LOW":
        explanation = "Passed: All checks within acceptable thresholds."
    else:
        explanation_parts = []
        if fraud_reasons:
            explanation_parts.append("FRAUD ALERTS: " + " | ".join(fraud_reasons))
        if offline_reasons:
            explanation_parts.append("SYSTEM ALERTS: " + " | ".join(offline_reasons))
        explanation = f"Flagged {risk_level}: " + " || ".join(explanation_parts)
        
    # --- 5. Numerical Score Calculation ---
    # Higher tamper = higher risk. Lower face match = higher risk.
    # We use base constants for missing data to push the numerical score to moderate ranges for review.
    base_tamper = tamper_score if tampering_status not in ["ANALYSIS_UNAVAILABLE", "PENDING"] else 0.5
    base_face = face_match_score if face_status in ["FACE_MATCH", "FACE_NO_MATCH"] else 0.5
    base_mrz_penalty = 0.2 if mrz_status == "MRZ_INVALID" else (0.1 if mrz_status != "MRZ_VALID" else 0.0)
    
    raw_risk_score = (
        (base_tamper * 0.4) + 
        ((1.0 - base_face) * 0.4) + 
        base_mrz_penalty
    )
    
    # Cap score
    numerical_risk = min(int(raw_risk_score * 100), 100)

    return {
        "risk_level": risk_level,
        "numerical_score": numerical_risk,
        "explanation": explanation,
        "is_flagged": risk_level != "LOW"
    }
