import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
import logging

logger = logging.getLogger("trustscan_audit")

async def log_audit_event(
    db: AsyncSession,
    event_type: str,
    scan_id: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    event_status: str = "SUCCESS",
    event_metadata: Optional[dict] = None
):
    """
    Safely logs an audit event to the database.
    Ensures that no raw images, face embeddings, passwords, or tokens are logged.
    """
    # Sanitize metadata just in case someone passes raw data
    safe_metadata = {}
    if event_metadata:
        for k, v in event_metadata.items():
            k_lower = k.lower()
            if any(bad in k_lower for bad in ["password", "token", "secret", "image", "embedding", "biometric"]):
                safe_metadata[k] = "[REDACTED]"
            else:
                safe_metadata[k] = v

    audit_entry = AuditLog(
        scan_id=scan_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        event_status=event_status,
        event_metadata=safe_metadata if safe_metadata else None
    )
    
    try:
        db.add(audit_entry)
        await db.commit()
    except Exception as e:
        await db.rollback()
        # Fallback to logger if DB is unavailable
        logger.error(f"Failed to persist audit log to DB: {e}. Audit Event: {event_type} for scan {scan_id}")
