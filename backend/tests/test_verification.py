import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from app.main import app
from app.db.session import get_db
from app.models.scan import Scan
from app.models.user import User
from app.core.security import create_access_token
from app.api.deps import get_current_user

client = TestClient(app)

@pytest.fixture
def valid_token():
    return create_access_token(subject="officer_123")

@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    # Create a mock scan
    mock_scan = MagicMock(spec=Scan)
    mock_scan.session_id = "SCAN-123"
    mock_scan.human_verification_status = "PENDING_REVIEW"
    mock_scan.risk_level = "MEDIUM"
    mock_scan.numerical_score = 50
    mock_scan.human_reviewer_id = None
    
    # Create a mock user
    mock_user = MagicMock(spec=User)
    mock_user.id = "officer_123"
    mock_user.role = "OFFICER"
    mock_user.is_active = True
    
    def execute_side_effect(stmt):
        mock_result = MagicMock()
        # If it's querying for a user
        if 'users' in str(stmt):
            mock_result.scalars.return_value.first.return_value = mock_user
        # If it's querying for a scan
        elif 'scans' in str(stmt):
            mock_result.scalars.return_value.first.return_value = mock_scan
        return mock_result
        
    mock_session.execute.side_effect = execute_side_effect
    
    return mock_session, mock_scan, mock_user

def override_get_db_with_mock(mock_session):
    async def _override():
        yield mock_session
    return _override

def test_unauthenticated_request(mock_db_session):
    response = client.post("/api/v1/verification/SCAN-123/approve")
    assert response.status_code == 401

def test_approve_existing_scan(mock_db_session, valid_token):
    mock_session, mock_scan, _ = mock_db_session
    app.dependency_overrides[get_db] = override_get_db_with_mock(mock_session)
    
    response = client.post("/api/v1/verification/SCAN-123/approve", headers={"Authorization": f"Bearer {valid_token}"}, json={"notes": "Looks good"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["human_verification_status"] == "APPROVED"
    assert "human_decision_at" in data
    
    # Ensure risk score unchanged
    assert mock_scan.risk_level == "MEDIUM"
    assert mock_scan.numerical_score == 50
    # Ensure officer ID is saved
    assert mock_scan.human_reviewer_id == "officer_123"

def test_reject_unauthorized_role(mock_db_session, valid_token):
    mock_session, mock_scan, mock_user = mock_db_session
    # Change role to REVIEWER, which is not allowed
    mock_user.role = "REVIEWER"
    app.dependency_overrides[get_db] = override_get_db_with_mock(mock_session)
    
    response = client.post("/api/v1/verification/SCAN-123/reject", headers={"Authorization": f"Bearer {valid_token}"})
    assert response.status_code == 403
    assert "Operation not permitted" in response.json()["detail"]
