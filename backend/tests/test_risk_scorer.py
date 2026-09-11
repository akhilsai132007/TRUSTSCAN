import pytest
from app.services.risk_scorer import calculate_risk_score

def test_scenario_a_clean_document():
    # A. Clean document: valid MRZ + no tampering indicators + matching face
    res = calculate_risk_score(
        mrz_status="MRZ_VALID",
        tampering_status="NO_TAMPERING_INDICATOR",
        tamper_score=0.1,
        face_status="FACE_MATCH",
        face_match_score=0.9,
        pipeline_errors=[]
    )
    assert res["risk_level"] == "LOW"
    assert "Passed:" in res["explanation"]

def test_scenario_b_mrz_checksum_failure():
    # B. MRZ checksum failure -> HIGH or MEDIUM
    res = calculate_risk_score(
        mrz_status="MRZ_INVALID",
        tampering_status="NO_TAMPERING_INDICATOR",
        tamper_score=0.1,
        face_status="FACE_MATCH",
        face_match_score=0.9,
        pipeline_errors=[]
    )
    assert res["risk_level"] == "MEDIUM"
    assert "MRZ checksum invalid" in res["explanation"]
    assert "FRAUD ALERTS:" in res["explanation"]

def test_scenario_c_tampering_detected():
    # C. Tampering detected -> HIGH or MEDIUM
    res = calculate_risk_score(
        mrz_status="MRZ_VALID",
        tampering_status="TAMPERING_DETECTED",
        tamper_score=0.95,
        face_status="FACE_MATCH",
        face_match_score=0.9,
        pipeline_errors=[]
    )
    assert res["risk_level"] == "HIGH" # 0.95 > TAMPER_EXTREME threshold triggers HIGH directly
    assert "Tampering detected" in res["explanation"]

def test_scenario_d_face_mismatch():
    # D. Face mismatch -> HIGH or MEDIUM
    res = calculate_risk_score(
        mrz_status="MRZ_VALID",
        tampering_status="NO_TAMPERING_INDICATOR",
        tamper_score=0.1,
        face_status="FACE_NO_MATCH",
        face_match_score=0.2,
        pipeline_errors=[]
    )
    assert res["risk_level"] == "MEDIUM"
    assert "Face mismatch" in res["explanation"]

def test_scenario_e_ocr_unavailable():
    # E. OCR unavailable -> REVIEW_REQUIRED (not fraud)
    res = calculate_risk_score(
        mrz_status="OCR_UNAVAILABLE",
        tampering_status="NO_TAMPERING_INDICATOR",
        tamper_score=0.1,
        face_status="FACE_MATCH",
        face_match_score=0.9,
        pipeline_errors=["OCR engine offline"]
    )
    assert res["risk_level"] == "REVIEW_REQUIRED"
    assert "SYSTEM ALERTS: OCR/MRZ unavailable" in res["explanation"]
    assert "FRAUD ALERTS" not in res["explanation"]

def test_scenario_f_multiple_suspicious_signals():
    # F. Multiple suspicious signals -> HIGH
    res = calculate_risk_score(
        mrz_status="MRZ_INVALID",
        tampering_status="NO_TAMPERING_INDICATOR",
        tamper_score=0.1,
        face_status="FACE_NO_MATCH",
        face_match_score=0.3,
        pipeline_errors=[]
    )
    assert res["risk_level"] == "HIGH" # 2 or more fraud factors = HIGH
    assert "MRZ checksum invalid" in res["explanation"]
    assert "Face mismatch" in res["explanation"]

def test_scenario_g_all_subsystems_unavailable():
    # G. All subsystems unavailable -> REVIEW_REQUIRED
    res = calculate_risk_score(
        mrz_status="OCR_UNAVAILABLE",
        tampering_status="ANALYSIS_UNAVAILABLE",
        tamper_score=1.0,
        face_status="FACE_ANALYSIS_UNAVAILABLE",
        face_match_score=0.0,
        pipeline_errors=["System crash", "Network timeout"]
    )
    assert res["risk_level"] == "REVIEW_REQUIRED"
    assert "OCR/MRZ unavailable" in res["explanation"]
    assert "Tamper analysis failed: ANALYSIS_UNAVAILABLE" in res["explanation"]
    assert "Face analysis inconclusive: FACE_ANALYSIS_UNAVAILABLE" in res["explanation"]
    assert "System errors: 2 detected" in res["explanation"]
    assert "FRAUD ALERTS" not in res["explanation"]
