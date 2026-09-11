import re
import os
from typing import Dict, Any, List, Tuple

def char_value(c: str) -> int:
    """Returns the integer value of an MRZ character for checksum calculation."""
    if c == '<':
        return 0
    if '0' <= c <= '9':
        return int(c)
    if 'A' <= c <= 'Z':
        return ord(c) - 55
    return 0

def calculate_checksum(data: str) -> int:
    """Calculates the ICAO 9303 checksum for a given string."""
    weights = [7, 3, 1]
    total = 0
    for i, char in enumerate(data):
        total += char_value(char) * weights[i % 3]
    return total % 10

def parse_td3_mrz(mrz_lines: List[str]) -> Dict[str, Any]:
    """
    Parses a TD3 (Passport) MRZ consisting of 2 lines of 44 characters.
    """
    if len(mrz_lines) != 2 or len(mrz_lines[0]) != 44 or len(mrz_lines[1]) != 44:
        raise ValueError("Invalid TD3 MRZ format. Must be 2 lines of 44 characters.")

    line1 = mrz_lines[0]
    line2 = mrz_lines[1]

    # Line 1 extraction
    doc_type = line1[0:2].replace('<', '')
    issuing_country = line1[2:5].replace('<', '')
    name_parts = line1[5:].split('<<')
    surname = name_parts[0].replace('<', ' ').strip()
    given_names = name_parts[1].replace('<', ' ').strip() if len(name_parts) > 1 else ""

    # Line 2 extraction
    doc_number = line2[0:9]
    doc_number_check = line2[9]
    nationality = line2[10:13].replace('<', '')
    dob = line2[13:19]
    dob_check = line2[19]
    sex = line2[20]
    expiry = line2[21:27]
    expiry_check = line2[27]
    personal_number = line2[28:42]
    personal_number_check = line2[42]
    composite_check = line2[43]

    return {
        "doc_type": doc_type,
        "issuing_country": issuing_country,
        "surname": surname,
        "given_name": given_names,
        "nationality": nationality,
        "sex": sex,
        "doc_number": doc_number,
        "doc_number_check": doc_number_check,
        "dob": dob,
        "dob_check": dob_check,
        "expiry": expiry,
        "expiry_check": expiry_check,
        "personal_number": personal_number,
        "personal_number_check": personal_number_check,
        "composite_check": composite_check,
        "raw_line1": line1,
        "raw_line2": line2
    }

def validate_mrz_checksums(parsed: Dict[str, Any]) -> Dict[str, bool]:
    """Validates the checksum digits of the parsed MRZ."""
    
    doc_num_valid = calculate_checksum(parsed['doc_number']) == char_value(parsed['doc_number_check'])
    dob_valid = calculate_checksum(parsed['dob']) == char_value(parsed['dob_check'])
    expiry_valid = calculate_checksum(parsed['expiry']) == char_value(parsed['expiry_check'])
    
    # Personal number validation depends on whether it's empty/filled with <
    if parsed['personal_number'].replace('<', '') == '':
        personal_valid = parsed['personal_number_check'] == '<' or char_value(parsed['personal_number_check']) == 0
    else:
        personal_valid = calculate_checksum(parsed['personal_number']) == char_value(parsed['personal_number_check'])

    # Composite check
    # Concatenates: doc_number + doc_check + dob + dob_check + expiry + expiry_check + personal_number + personal_check
    composite_data = (parsed['doc_number'] + parsed['doc_number_check'] +
                      parsed['dob'] + parsed['dob_check'] +
                      parsed['expiry'] + parsed['expiry_check'] +
                      parsed['personal_number'] + parsed['personal_number_check'])
    
    composite_valid = calculate_checksum(composite_data) == char_value(parsed['composite_check'])

    return {
        "doc_number_valid": doc_num_valid,
        "dob_valid": dob_valid,
        "expiry_valid": expiry_valid,
        "personal_number_valid": personal_valid,
        "composite_valid": composite_valid,
        "all_valid": doc_num_valid and dob_valid and expiry_valid and personal_valid and composite_valid
    }

def cross_check_mrz_vs_ocr(parsed_mrz: Dict[str, Any], checksum_validations: Dict[str, bool], ocr_vz_data: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Cross-checks MRZ parsed data against OCR Visual Zone data.
    Returns a structured result as requested.
    """
    results = []

    fields_to_check = [
        ("surname", "surname"),
        ("given_name", "given_name"),
        ("dob", "dob"),
        ("doc_number", "doc_number")
    ]

    for mrz_field, ocr_field in fields_to_check:
        mrz_val = parsed_mrz.get(mrz_field, "").upper().replace('<', '')
        vz_val = ocr_vz_data.get(ocr_field, "").upper()
        
        # Determine if checksum exists for this field
        check_field_map = {
            "dob": "dob_valid",
            "doc_number": "doc_number_valid"
        }
        
        is_checksum_valid = True
        if mrz_field in check_field_map:
            is_checksum_valid = checksum_validations.get(check_field_map[mrz_field], False)

        # Handle dates formatting (MRZ is YYMMDD, VZ could be anything, but assuming standardized YYMMDD here for simplicity)
        match = mrz_val == vz_val
        
        # Looser match for names (MRZ names might be truncated)
        if mrz_field in ("surname", "given_name"):
            match = mrz_val in vz_val or vz_val in mrz_val
            
            # Names don't have checksums in MRZ
            is_checksum_valid = True 

        results.append({
            "field": mrz_field,
            "mrz_value": mrz_val,
            "vz_value": vz_val,
            "match": match,
            "checksum_valid": is_checksum_valid
        })

    return results

def extract_mrz_from_image(image_path: str) -> Tuple[List[str], str]:
    """
    Extracts MRZ lines and raw OCR text from an image using Tesseract.
    Returns (mrz_lines, raw_text).
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise ImportError("pytesseract and Pillow are required for image extraction")

    try:
        image = Image.open(image_path)
        # Using specific tesseract config for MRZ OCR
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<'
        text = pytesseract.image_to_string(image, config=custom_config)
    except pytesseract.pytesseract.TesseractNotFoundError:
        raise RuntimeError("OCR_UNAVAILABLE")
    except Exception as e:
        raise RuntimeError(f"OCR_FAILED: {str(e)}")
    
    # Simple regex to find 44-character MRZ lines for TD3
    lines = [line.strip() for line in text.split('\n')]
    mrz_lines = [line for line in lines if len(line) == 44 and re.match(r'^[A-Z0-9<]+$', line)]
    
    if len(mrz_lines) >= 2:
        return mrz_lines[-2:], text
    return [], text

def process_document(image_path: str, ocr_vz_data: Dict[str, str]) -> Dict[str, Any]:
    """Orchestrates extraction, parsing, validation, and cross-checking."""
    try:
        mrz_lines, raw_text = extract_mrz_from_image(image_path)
    except RuntimeError as e:
        # e.g. OCR_UNAVAILABLE
        return {"error": str(e), "raw_ocr_text": ""}
        
    if not mrz_lines:
        return {"error": "No MRZ found in image", "raw_ocr_text": raw_text}
        
    parsed = parse_td3_mrz(mrz_lines)
    checksums = validate_mrz_checksums(parsed)
    cross_check_results = cross_check_mrz_vs_ocr(parsed, checksums, ocr_vz_data)
    
    return {
        "mrz_parsed": parsed,
        "checksum_validation": checksums,
        "cross_check": cross_check_results,
        "raw_ocr_text": raw_text
    }
