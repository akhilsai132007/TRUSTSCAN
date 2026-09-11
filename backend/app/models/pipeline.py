import enum
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class SessionStatus(enum.Enum):
    PROCESSING = "PROCESSING"
    AUTO_APPROVED = "AUTO_APPROVED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECTED = "REJECTED"

class DecisionType(enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ScanSession(Base):
    """
    Forensically sound parent record for a document scan session.
    """
    __tablename__ = "scan_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_ip = Column(String)
    doc_hash = Column(String, index=True, nullable=False, doc="SHA256 of the original uploaded document")
    live_face_hash = Column(String, doc="SHA256 of the live face image")
    status = Column(Enum(SessionStatus), default=SessionStatus.PROCESSING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PipelineEvent(Base):
    """
    Append-only ledger of every AI stage execution.
    """
    __tablename__ = "pipeline_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("scan_sessions.id"), nullable=False, index=True)
    stage_name = Column(String, nullable=False)
    input_payload = Column(JSONB, nullable=False)
    output_payload = Column(JSONB, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OfficerDecision(Base):
    """
    Human review ledger, requires digital signature for accountability.
    """
    __tablename__ = "officer_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("scan_sessions.id"), nullable=False, index=True)
    officer_id = Column(String, nullable=False)
    decision = Column(Enum(DecisionType), nullable=False)
    rejection_reason = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    digital_signature = Column(Text, nullable=False, doc="Cryptographic signature of the decision data")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
