import logging
import time
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# Set up logging for audit
logger = logging.getLogger("trustscan_audit")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# Timeouts in seconds
TIMEOUT_OCR = 2.0
TIMEOUT_MRZ = 1.0
TIMEOUT_TAMPER = 2.0
TIMEOUT_FACE = 1.5

def run_with_timeout(func, timeout_sec, *args, **kwargs):
    """Executes a function with a strict timeout using ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_sec)
        except TimeoutError:
            logger.error(f"Stage Timeout: {func.__name__} exceeded {timeout_sec}s")
            raise TimeoutError(f"Stage timed out after {timeout_sec}s")
        except Exception as e:
            logger.error(f"Stage Exception in {func.__name__}: {str(e)}")
            raise e

# --- ACTUAL PIPELINE ORCHESTRATOR ---
def execute_scan_pipeline(session_id: str, file_path: str, live_image_path: Optional[str] = None) -> Dict[str, Any]:
    logger.info(f"Session {session_id}: Pipeline Started")
    
    results = {
        "mrz_valid": False, # Fail closed
        "face_match_score": 0.0, # Fail closed
        "tamper_score": 1.0, # Fail closed (assume max tamper if error)
        "metadata_score": 0.0, # Assume no anomaly unless set
        "ocr_confidence": 0.0,
        "raw_ocr_text": "",
        "mrz_status": "PENDING",
        "mrz_validation_details": None,
        "critical_pipeline_errors": []
    }
    
    # 1. OCR Extraction (REAL MODE)
    try:
        from app.services.mrz_service import process_document
        doc_data = process_document(file_path, {})
        results["raw_ocr_text"] = doc_data.get("raw_ocr_text", "")
        
        if "error" in doc_data:
            results["critical_pipeline_errors"].append(doc_data["error"])
            results["ocr_confidence"] = 0.0
            results["mrz_valid"] = False
            if "OCR_UNAVAILABLE" in doc_data["error"]:
                results["mrz_status"] = "OCR_UNAVAILABLE"
            elif "No MRZ found" in doc_data["error"]:
                results["mrz_status"] = "MRZ_NOT_FOUND"
            else:
                results["mrz_status"] = "MRZ_ERROR"
        else:
            results["ocr_confidence"] = 0.95 # Assume high for real extraction if it succeeded
            is_valid = doc_data["checksum_validation"]["all_valid"]
            results["mrz_valid"] = is_valid
            results["mrz_status"] = "MRZ_VALID" if is_valid else "MRZ_INVALID"
            
            results["mrz_validation_details"] = {
                "doc_number_valid": doc_data["checksum_validation"]["doc_number_valid"],
                "dob_valid": doc_data["checksum_validation"]["dob_valid"],
                "expiry_valid": doc_data["checksum_validation"]["expiry_valid"],
                "personal_number_valid": doc_data["checksum_validation"]["personal_number_valid"],
                "composite_valid": doc_data["checksum_validation"]["composite_valid"]
            }
    except Exception as e:
        results["critical_pipeline_errors"].append(f"OCR Stage Failed: {str(e)}")

    # 2. Tamper Detection (REAL MODE)
    results["tampering_status"] = "PENDING"
    results["tampering_method"] = ""
    results["suspicious_regions"] = []
    
    try:
        from app.services.tamper_service import analyze_image
        tamper_res = analyze_image(file_path)
        results["tamper_score"] = tamper_res.get("tampering_score", 1.0)
        results["tampering_status"] = tamper_res.get("tampering_status", "ANALYSIS_UNAVAILABLE")
        results["tampering_method"] = tamper_res.get("method_used", "")
        results["suspicious_regions"] = tamper_res.get("suspicious_regions", [])
        
        if "error" in tamper_res:
            results["critical_pipeline_errors"].append(f"Tamper Stage Alert: {tamper_res['error']}")
    except Exception as e:
        results["critical_pipeline_errors"].append(f"Tamper Stage Failed: {str(e)}")
        results["tampering_status"] = "ANALYSIS_UNAVAILABLE"

    # 3. Face Verification (REAL MODE)
    results["face_status"] = "PENDING"
    
    try:
        if live_image_path:
            from app.services.face_service import verify_faces
            face_res = verify_faces(file_path, live_image_path)
            
            results["face_status"] = face_res.get("face_status", "FACE_ANALYSIS_UNAVAILABLE")
            results["face_match_score"] = face_res.get("similarity_score", 0.0)
            
            if "error" in face_res:
                results["critical_pipeline_errors"].append(f"Face Stage Alert: {face_res['error']}")
        else:
            results["face_status"] = "FACE_NOT_FOUND"
            results["face_match_score"] = 0.0
            results["critical_pipeline_errors"].append("Live selfie image missing for face comparison.")
                 
    except Exception as e:
        results["critical_pipeline_errors"].append(f"Face Stage Failed: {str(e)}")
        results["face_status"] = "FACE_ANALYSIS_UNAVAILABLE"

    # 4. Risk Scoring
    from app.services.risk_scorer import calculate_risk_score
    
    final_risk = calculate_risk_score(
        mrz_status=results["mrz_status"],
        tampering_status=results["tampering_status"],
        tamper_score=results["tamper_score"],
        face_status=results["face_status"],
        face_match_score=results["face_match_score"],
        pipeline_errors=results["critical_pipeline_errors"]
    )
        
    logger.info(f"Session {session_id}: Pipeline Finished. Risk: {final_risk['risk_level']}")
    
    return {
        "session_id": session_id,
        "pipeline_data": results,
        "risk_decision": final_risk
    }


# --- MOCK DEMO STAGES ---

def call_ocr_engine(image_bytes: bytes) -> Dict[str, Any]:
    if b"CORRUPTED" in image_bytes:
        raise ValueError("Cannot decode image bytes")
    if b"BLURRY" in image_bytes:
        return {"extracted": None, "confidence": 0.2}
    if b"UNSUPPORTED" in image_bytes:
        return {"extracted": None, "confidence": 0.0}
    if b"TIMEOUT_OCR" in image_bytes:
        time.sleep(3)
    
    return {
        "extracted": {"surname": "DOE", "given_name": "JOHN", "dob": "800101", "doc_number": "L898902C3"},
        "mrz_lines": ["P<USA<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", "L898902C36USA8001012M3001019<<<<<<<<<<<<<<00"],
        "confidence": 0.95
    }

def call_tamper_engine(image_bytes: bytes) -> Dict[str, Any]:
    if b"TIMEOUT_TAMPER" in image_bytes:
        time.sleep(3)
    return {"tamper_probability": 0.1, "confidence": 0.9}

def call_face_engine(doc_image: bytes, live_image: bytes) -> Dict[str, Any]:
    if b"NO_FACE" in doc_image or b"NO_FACE" in live_image:
        return {"match": False, "similarity_score": 0.0, "confidence": 0.99, "error": "Face not detected"}
    if b"MISMATCH" in live_image:
        return {"match": False, "similarity_score": 0.3, "confidence": 0.95}
    return {"match": True, "similarity_score": 0.98, "confidence": 0.95}


def execute_demo_pipeline(session_id: str, doc_image: bytes, live_image: bytes) -> Dict[str, Any]:
    """Isolated Demo pipeline using only mock byte strings."""
    logger.info(f"Session {session_id}: DEMO Pipeline Started")
    
    results = {
        "mrz_valid": False,
        "face_match_score": 0.0,
        "tamper_score": 1.0,
        "metadata_score": 0.0,
        "ocr_confidence": 0.0,
        "raw_ocr_text": "",
        "mrz_status": "PENDING",
        "mrz_validation_details": None,
        "critical_pipeline_errors": []
    }
    
    try:
        ocr_res = run_with_timeout(call_ocr_engine, TIMEOUT_OCR, doc_image)
        results["ocr_confidence"] = ocr_res.get("confidence", 0.0)
        
        if results["ocr_confidence"] < 0.6:
            results["critical_pipeline_errors"].append("OCR confidence too low")
        else:
            results["mrz_valid"] = b"BAD_MRZ" not in doc_image
            results["mrz_status"] = "MRZ_VALID" if results["mrz_valid"] else "MRZ_INVALID"
    except Exception as e:
        results["critical_pipeline_errors"].append(f"OCR Stage Failed: {str(e)}")

    try:
        tamper_res = run_with_timeout(call_tamper_engine, TIMEOUT_TAMPER, doc_image)
        results["tamper_score"] = tamper_res.get("tamper_probability", 1.0)
        results["tampering_status"] = "TAMPERING_DETECTED" if results["tamper_score"] >= 0.4 else "NO_TAMPERING_INDICATOR"
        results["tampering_method"] = "Mock Engine"
    except Exception as e:
        results["critical_pipeline_errors"].append(f"Tamper Stage Failed: {str(e)}")
        results["tampering_status"] = "ANALYSIS_UNAVAILABLE"

    try:
        face_res = run_with_timeout(call_face_engine, TIMEOUT_FACE, doc_image, live_image)
        results["face_match_score"] = face_res.get("similarity_score", 0.0)
        results["face_status"] = "FACE_MATCH" if results["face_match_score"] > 0.75 else "FACE_NO_MATCH"
        if "error" in face_res:
             results["critical_pipeline_errors"].append(f"Face Stage Error: {face_res['error']}")
    except Exception as e:
        results["critical_pipeline_errors"].append(f"Face Stage Failed: {str(e)}")
        results["face_status"] = "FACE_ANALYSIS_UNAVAILABLE"

    from app.services.risk_scorer import calculate_risk_score
    final_risk = calculate_risk_score(
        mrz_status=results["mrz_status"],
        tampering_status=results["tampering_status"],
        tamper_score=results["tamper_score"],
        face_status=results["face_status"],
        face_match_score=results["face_match_score"],
        pipeline_errors=results["critical_pipeline_errors"]
    )
        
    return {
        "session_id": session_id,
        "pipeline_data": results,
        "risk_decision": final_risk
    }
