from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid

# Stage 1: OCR Extraction
class OcrInput(BaseModel):
    session_id: uuid.UUID
    image_url: str
    doc_type: str

class OcrExtractedText(BaseModel):
    given_name: Optional[str] = None
    surname: Optional[str] = None
    dob: Optional[str] = None
    document_number: Optional[str] = None
    expiry_date: Optional[str] = None

class OcrOutput(BaseModel):
    extracted_text: OcrExtractedText
    mrz_raw: Optional[str] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)

# Stage 2: MRZ / Structural Validation
class MrzInput(BaseModel):
    mrz_raw: str
    extracted_text: OcrExtractedText

class MrzOutput(BaseModel):
    is_mrz_valid: bool
    checksum_errors: List[str] = []
    cross_check_match: bool

# Stage 3: AI Tampering Detection
class TamperingInput(BaseModel):
    image_url: str

class TamperingOutput(BaseModel):
    tamper_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    anomalies_detected: List[str] = []
    heatmap_url: Optional[str] = None

# Stage 4: Face Verification
class FaceVerificationInput(BaseModel):
    document_image_url: str
    live_face_url: str

class FaceVerificationOutput(BaseModel):
    faces_detected: bool
    match: bool
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    liveness_check: Optional[str] = None

# Stage 5: Risk Score Fusion
class RiskScoreInput(BaseModel):
    ocr_data: OcrOutput
    mrz_data: MrzOutput
    tamper_data: TamperingOutput
    face_data: FaceVerificationOutput

class RiskScoreOutput(BaseModel):
    final_risk_score: int = Field(..., ge=0, le=100)
    risk_level: str  # LOW, MEDIUM, HIGH
    flagged_reasons: List[str] = []
