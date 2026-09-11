from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Core
    PROJECT_NAME: str = "TRUSTSCAN API"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/trustscan"
    
    # Risk Thresholds
    THRESHOLD_FACE_MATCH: float = 0.75
    THRESHOLD_TAMPER: float = 0.40
    THRESHOLD_TAMPER_EXTREME: float = 0.80
    THRESHOLD_METADATA: float = 0.50
    
    # Auth
    SECRET_KEY: str # IN PRODUCTION: Must be provided via environment
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    
    # Storage
    MAX_UPLOAD_SIZE_MB: int = 5
    DOCUMENT_RETENTION_ENABLED: bool = False
    DOCUMENT_RETENTION_HOURS: int = 24
    STORAGE_PROVIDER: str = "LOCAL" # Options: LOCAL, AZURE
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "trustscan-documents"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
