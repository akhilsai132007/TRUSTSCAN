import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app
from app.db.session import get_db
from app.models.scan import Scan
from app.models.user import User
from app.models.audit import AuditLog
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    
    mock_scan = MagicMock(spec=Scan)
    mock_scan.session_id = "SCAN-123"
    mock_scan.human_verification_status = "PENDING_REVIEW"
    
    mock_user = MagicMock(spec=User)
    mock_user.id = "officer_123"
    mock_user.role = "OFFICER"
    mock_user.is_active = True
    
    def execute_side_effect(stmt):
        mock_result = MagicMock()
        if 'users' in str(stmt):
            mock_result.scalars.return_value.first.return_value = mock_user
        elif 'scans' in str(stmt) and 'audit_logs' not in str(stmt):
            mock_result.scalars.return_value.first.return_value = mock_scan
        elif 'audit_logs' in str(stmt):
            mock_audit = MagicMock(spec=AuditLog)
            mock_audit.event_type = "SCAN_APPROVED"
            mock_audit.timestamp = "2026-09-11T12:00:00Z"
            mock_audit.actor_user_id = "officer_123"
            mock_audit.event_status = "SUCCESS"
            mock_audit.event_metadata = {}
            mock_result.scalars.return_value.all.return_value = [mock_audit]
        return mock_result
        
    mock_session.execute.side_effect = execute_side_effect
    return mock_session, mock_scan, mock_user

def override_get_db_with_mock(mock_session):
    async def _override():
        yield mock_session
    return _override

def test_audit_history_requires_auth(mock_db_session):
    mock_session, _, _ = mock_db_session
    app.dependency_overrides[get_db] = override_get_db_with_mock(mock_session)
    
    response = client.get("/api/v1/scans/SCAN-123/audit")
    assert response.status_code == 401

def test_audit_history_success(mock_db_session):
    mock_session, _, _ = mock_db_session
    app.dependency_overrides[get_db] = override_get_db_with_mock(mock_session)
    token = create_access_token(subject="officer_123")
    
    response = client.get("/api/v1/scans/SCAN-123/audit", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "SCAN_APPROVED"
    assert data["events"][0]["actor"] == "officer_123"

@patch('app.api.routes.log_audit_event')
def test_approve_creates_audit_event(mock_log, mock_db_session):
    mock_session, _, _ = mock_db_session
    app.dependency_overrides[get_db] = override_get_db_with_mock(mock_session)
    token = create_access_token(subject="officer_123")
    
    response = client.post("/api/v1/verification/SCAN-123/approve", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    
    # Verify the audit log was called correctly
    assert mock_log.called
    kwargs = mock_log.call_args.kwargs
    assert kwargs["event_type"] == "SCAN_APPROVED"
    assert kwargs["actor_user_id"] == "officer_123"
    assert kwargs["scan_id"] == "SCAN-123"
