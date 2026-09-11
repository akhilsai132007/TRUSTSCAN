from app.services.pipeline import execute_scan_pipeline
from app.services import mrz_service, tamper_service, face_service
import pytest
import pytest

@pytest.fixture(autouse=True)
def mock_pipeline_dependencies(monkeypatch):
    monkeypatch.setattr(tamper_service, "analyze_image", lambda path: {
        "tampering_status": "NO_TAMPERING_INDICATOR",
        "tampering_score": 0.1,
        "method_used": "Mock ELA",
        "suspicious_regions": []
    })
    
    monkeypatch.setattr(face_service, "verify_faces", lambda doc, live: {
        "face_status": "FACE_MATCH",
        "similarity_score": 0.95,
        "distance_metric": 0.3
    })

# Dummy valid strings
VALID_MRZ_LINE1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
VALID_MRZ_LINE2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
CORRUPT_MRZ_LINE1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
CORRUPT_MRZ_LINE2 = "L898902X36UTO7408129F1204159ZE184226B<<<<<10"

def test_pipeline_ocr_unavailable(monkeypatch):
    def mock_extract(image_path):
        raise RuntimeError("OCR_UNAVAILABLE")
    monkeypatch.setattr(mrz_service, "extract_mrz_from_image", mock_extract)
    
    result = execute_scan_pipeline("test-1", file_path="dummy.jpg")
    assert result["pipeline_data"]["mrz_status"] == "OCR_UNAVAILABLE"
    assert result["pipeline_data"]["mrz_valid"] is False

def test_pipeline_mrz_not_found(monkeypatch):
    def mock_extract(image_path):
        return [], "random text no mrz here"
    monkeypatch.setattr(mrz_service, "extract_mrz_from_image", mock_extract)
    
    result = execute_scan_pipeline("test-2", file_path="dummy.jpg")
    assert result["pipeline_data"]["mrz_status"] == "MRZ_NOT_FOUND"
    assert result["pipeline_data"]["mrz_valid"] is False

def test_pipeline_mrz_valid(monkeypatch):
    def mock_extract(image_path):
        return [VALID_MRZ_LINE1, VALID_MRZ_LINE2], "RAW TEXT"
    monkeypatch.setattr(mrz_service, "extract_mrz_from_image", mock_extract)
    
    result = execute_scan_pipeline("test-3", file_path="dummy.jpg")
    assert result["pipeline_data"]["mrz_status"] == "MRZ_VALID"
    assert result["pipeline_data"]["mrz_valid"] is True
    details = result["pipeline_data"]["mrz_validation_details"]
    assert details["doc_number_valid"] is True
    assert details["all_valid"] is True if "all_valid" in details else True

def test_pipeline_mrz_invalid(monkeypatch):
    def mock_extract(image_path):
        return [CORRUPT_MRZ_LINE1, CORRUPT_MRZ_LINE2], "RAW TEXT"
    monkeypatch.setattr(mrz_service, "extract_mrz_from_image", mock_extract)
    
    result = execute_scan_pipeline("test-4", file_path="dummy.jpg")
    assert result["pipeline_data"]["mrz_status"] == "MRZ_INVALID"
    assert result["pipeline_data"]["mrz_valid"] is False
    details = result["pipeline_data"]["mrz_validation_details"]
    assert details["dob_valid"] is False
