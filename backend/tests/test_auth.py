import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from app.main import app
from app.db.session import get_db
from app.core.security import get_password_hash, verify_password, create_access_token

client = TestClient(app)

def test_password_hashing():
    password = "securepassword123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_token_creation():
    token = create_access_token(subject="user_123")
    assert isinstance(token, str)
    assert len(token) > 0

def test_login_success():
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user1"
    mock_user.username = "admin"
    mock_user.hashed_password = get_password_hash("password")
    mock_user.is_active = True
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    async def override_get_db():
        yield mock_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    response = client.post("/api/v1/login/access-token", data={"username": "admin", "password": "password"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
def test_login_invalid_password():
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user1"
    mock_user.username = "admin"
    mock_user.hashed_password = get_password_hash("password")
    mock_user.is_active = True
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    async def override_get_db():
        yield mock_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    response = client.post("/api/v1/login/access-token", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 400
    assert "Incorrect username or password" in response.json()["detail"]

def test_login_inactive_user():
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.username = "admin"
    mock_user.hashed_password = get_password_hash("password")
    mock_user.is_active = False
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    async def override_get_db():
        yield mock_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    response = client.post("/api/v1/login/access-token", data={"username": "admin", "password": "password"})
    assert response.status_code == 400
    assert "Inactive user" in response.json()["detail"]
