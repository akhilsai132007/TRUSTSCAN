import uuid
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from app.db.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, index=True, nullable=True) # Nullable for auth failures
    event_type = Column(String, index=True, nullable=False)
    actor_user_id = Column(String, index=True, nullable=True) # Nullable for system events
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    event_status = Column(String, default="SUCCESS", nullable=False)
    event_metadata = Column(JSON, nullable=True)
