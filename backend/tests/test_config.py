import pytest
from app.core.config import Settings

def test_database_url_normalization_postgres():
    """Verify that postgres:// is normalized to postgresql+asyncpg://"""
    settings = Settings(DATABASE_URL="postgres://user:pass@localhost:5432/db")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"

def test_database_url_normalization_postgresql():
    """Verify that postgresql:// is normalized to postgresql+asyncpg://"""
    settings = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"

def test_database_url_normalization_already_asyncpg():
    """Verify that postgresql+asyncpg:// is untouched"""
    settings = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"
