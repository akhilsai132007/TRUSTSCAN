import pytest
from app.services.mrz_service import parse_td3_mrz, validate_mrz_checksums, cross_check_mrz_vs_ocr

# Valid TD3 sample from Wikipedia (Utopia Passport)
VALID_MRZ_LINE1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
VALID_MRZ_LINE2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"

# Corrupted MRZ sample (changed checksums and values)
CORRUPT_MRZ_LINE1 = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<"
# Original Doc Number: L898902C3, check: 6
# Corrupting Doc Number to L898902X3, keeping check 6 (should fail)
# Original DOB: 740812, check: 2
# Corrupting DOB check to 9 (should fail)
CORRUPT_MRZ_LINE2 = "L898902X36UTO7408129F1204159ZE184226B<<<<<10"

def test_parse_valid_mrz():
    parsed = parse_td3_mrz([VALID_MRZ_LINE1, VALID_MRZ_LINE2])
    assert parsed['doc_type'] == "P"
    assert parsed['issuing_country'] == "UTO"
    assert parsed['surname'] == "ERIKSSON"
    assert parsed['given_name'] == "ANNA MARIA"
    assert parsed['doc_number'] == "L898902C3"
    assert parsed['doc_number_check'] == "6"
    assert parsed['nationality'] == "UTO"
    assert parsed['dob'] == "740812"
    assert parsed['dob_check'] == "2"
    assert parsed['sex'] == "F"
    assert parsed['expiry'] == "120415"
    assert parsed['expiry_check'] == "9"
    assert parsed['personal_number'] == "ZE184226B<<<<<"
    assert parsed['composite_check'] == "0"

def test_validate_valid_mrz_checksums():
    parsed = parse_td3_mrz([VALID_MRZ_LINE1, VALID_MRZ_LINE2])
    checksums = validate_mrz_checksums(parsed)
    assert checksums['doc_number_valid'] is True
    assert checksums['dob_valid'] is True
    assert checksums['expiry_valid'] is True
    assert checksums['personal_number_valid'] is True
    assert checksums['composite_valid'] is True
    assert checksums['all_valid'] is True

def test_validate_corrupted_mrz_checksums():
    parsed = parse_td3_mrz([CORRUPT_MRZ_LINE1, CORRUPT_MRZ_LINE2])
    checksums = validate_mrz_checksums(parsed)
    assert checksums['doc_number_valid'] is False
    assert checksums['dob_valid'] is False
    assert checksums['all_valid'] is False

def test_cross_check_mrz_vs_ocr_match():
    parsed = parse_td3_mrz([VALID_MRZ_LINE1, VALID_MRZ_LINE2])
    checksums = validate_mrz_checksums(parsed)
    
    ocr_data = {
        "surname": "ERIKSSON",
        "given_name": "ANNA MARIA",
        "dob": "740812",
        "doc_number": "L898902C3"
    }
    
    results = cross_check_mrz_vs_ocr(parsed, checksums, ocr_data)
    
    assert len(results) == 4
    for res in results:
        assert res['match'] is True
        assert res['checksum_valid'] is True

def test_cross_check_mrz_vs_ocr_mismatch():
    parsed = parse_td3_mrz([VALID_MRZ_LINE1, VALID_MRZ_LINE2])
    checksums = validate_mrz_checksums(parsed)
    
    ocr_data = {
        "surname": "ERIKSSON",
        "given_name": "BOB", # Mismatch
        "dob": "740815", # Mismatch
        "doc_number": "L898902C3"
    }
    
    results = cross_check_mrz_vs_ocr(parsed, checksums, ocr_data)
    
    for res in results:
        if res['field'] == 'dob':
            assert res['match'] is False
            assert res['checksum_valid'] is True
        elif res['field'] == 'given_name':
            assert res['match'] is False
            assert res['checksum_valid'] is True

def test_process_document_returns_raw_ocr(monkeypatch):
    from app.services import mrz_service
    # Mock extract_mrz_from_image to return dummy lines and raw text
    def mock_extract(image_path):
        return [VALID_MRZ_LINE1, VALID_MRZ_LINE2], "RAW_OCR_MOCK_DATA"
    
    monkeypatch.setattr(mrz_service, "extract_mrz_from_image", mock_extract)
    
    result = mrz_service.process_document("dummy.jpg", {})
    assert "error" not in result
    assert result["raw_ocr_text"] == "RAW_OCR_MOCK_DATA"
    assert result["mrz_parsed"]["doc_number"] == "L898902C3"

def test_process_document_handles_ocr_unavailable(monkeypatch):
    from app.services import mrz_service
    # Mock extract_mrz_from_image to throw RuntimeError("OCR_UNAVAILABLE")
    def mock_extract(image_path):
        raise RuntimeError("OCR_UNAVAILABLE")
    
    monkeypatch.setattr(mrz_service, "extract_mrz_from_image", mock_extract)
    
    result = mrz_service.process_document("dummy.jpg", {})
    assert "error" in result
    assert result["error"] == "OCR_UNAVAILABLE"
    assert result["raw_ocr_text"] == ""
