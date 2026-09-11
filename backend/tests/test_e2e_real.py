import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app
from app.db.session import get_db
from app.models.scan import Scan
import io

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    def execute_side_effect(stmt):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        return mock_result
    mock_session.execute.side_effect = execute_side_effect
    return mock_session

def override_get_db_with_mock(mock_session):
    async def _override():
        yield mock_session
    return _override

@pytest.mark.asyncio
async def test_real_upload_pipeline_e2e(mock_db_session):
    """
    Tests the real pipeline without mocking execute_scan_pipeline.
    We only mock the external boundary (the database) to verify the internal logic 
    handles the file correctly.
    """
    app.dependency_overrides[get_db] = override_get_db_with_mock(mock_db_session)
    
    # 1. Create a synthetic valid JPEG
    # This represents a real file upload.
    # We don't mock execute_scan_pipeline. It will run through the real modules.
    # Since Tesseract and dlib are likely missing, it will gracefully fall back to UNAVAILABLE.
    
    synthetic_image = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xd2\x7f\xff\xd9"
    file = io.BytesIO(synthetic_image)
    
    response = client.post(
        "/api/v1/scan/upload", 
        files={"document_image": ("synthetic.jpg", file, "image/jpeg")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "session_id" in data
    assert "pipeline_data" in data
    assert "risk_decision" in data
    
    pipeline = data["pipeline_data"]
    
    # 2. Assert no fake mocks were returned
    # The image is real but tiny, OCR will fail or find nothing.
    assert pipeline["mrz_status"] in ["OCR_UNAVAILABLE", "MRZ_NOT_FOUND", "MRZ_ERROR"]
    
    # Tamper service uses PIL, so it will likely run and return NO_TAMPERING_INDICATOR or INVALID_IMAGE.
    assert pipeline["tampering_status"] in ["NO_TAMPERING_INDICATOR", "TAMPERING_DETECTED", "ANALYSIS_UNAVAILABLE", "INVALID_IMAGE"]
    assert pipeline["tampering_method"] != "Mock Engine" # MUST NOT be the demo mock
    
    # Face service will be FACE_ANALYSIS_UNAVAILABLE or FACE_NOT_FOUND since there's no live image provided by /scan/upload
    assert pipeline["face_status"] in ["FACE_NOT_FOUND", "FACE_ANALYSIS_UNAVAILABLE"]
    
    # 3. Verify Risk Scorer
    risk = data["risk_decision"]
    # With missing OCR/Face, risk should escalate to REVIEW_REQUIRED
    assert risk["risk_level"] in ["REVIEW_REQUIRED", "MEDIUM", "HIGH"]
    
    # 4. Cleanup
    app.dependency_overrides.pop(get_db, None)
