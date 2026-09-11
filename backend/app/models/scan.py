from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    
    # Execution states
    status = Column(String, default="PENDING")
    
    # Core Risk Scoring
    risk_level = Column(String, nullable=True) # LOW, MEDIUM, HIGH, REVIEW_REQUIRED
    numerical_score = Column(Integer, nullable=True)
    explanation = Column(Text, nullable=True)
    
    # Subsystem states
    mrz_status = Column(String, nullable=True)
    tampering_status = Column(String, nullable=True)
    face_status = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Human Verification
    human_verification_status = Column(String, default="PENDING_REVIEW")
    human_decision = Column(String, nullable=True) # APPROVED, REJECTED, ESCALATED
    human_decision_at = Column(DateTime(timezone=True), nullable=True)
    human_reviewer_id = Column(String, nullable=True)
    
    # NOTE: We explicitly DO NOT store raw_ocr_text or raw facial embeddings in PostgreSQL.
    # If required for auditing later, those should be saved in secure blob storage (S3) 
    # referenced by this scan_id.
    document_storage_id = Column(String, nullable=True)
    document_file_size = Column(Integer, nullable=True)
    document_content_type = Column(String, nullable=True)
