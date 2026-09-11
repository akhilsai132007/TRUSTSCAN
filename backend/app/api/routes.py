from fastapi import APIRouter, HTTPException, BackgroundTasks, File, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.scan import Scan
from pydantic import BaseModel
import uuid
import os
import shutil
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("trustscan_audit")
from app.services.pipeline import execute_scan_pipeline, execute_demo_pipeline
from app.services.audit_service import log_audit_event
from app.services.storage import get_storage_service
from app.core.config import settings
from fastapi.responses import FileResponse

router = APIRouter()



class DemoScanRequest(BaseModel):
    case_type: str  # "clean", "borderline", "tampered"

@router.post("/scan/demo")
async def execute_demo_scan(request: DemoScanRequest):
    """
    Executes the pipeline synchronously for demo purposes based on case type.
    """
    session_id = f"DEMO-{str(uuid.uuid4())[:8].upper()}"
    
    # Map case types to byte sequences that trigger the QA mocked AI engines
    if request.case_type == "clean":
        doc_bytes = b"PERFECT"
        live_bytes = b"MATCHING"
    elif request.case_type == "tampered":
        doc_bytes = b"BAD_MRZ TIMEOUT_TAMPER" # Will trigger MRZ failure and extreme tamper
        live_bytes = b"MATCHING"
    elif request.case_type == "borderline":
        doc_bytes = b"PERFECT"
        live_bytes = b"MISMATCH" # Triggers low face match score -> MEDIUM risk
    else:
        raise HTTPException(status_code=400, detail="Invalid case type")
        
    result = execute_demo_pipeline(session_id, doc_image=doc_bytes, live_image=live_bytes)
    return result

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/scan/upload")
async def upload_and_scan(
    document_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Real file upload endpoint for processing actual documents.
    """
    # 1. Validate file size and type
    if document_image.size is not None and document_image.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB}MB.")
        
    allowed_types = ["image/jpeg", "image/png"]
    if document_image.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG and PNG are allowed.")
        
    session_id = f"SCAN-{str(uuid.uuid4())[:8].upper()}"
    file_ext = document_image.filename.split('.')[-1].lower()
    
    # Generate random internal filename to prevent path traversal & leaking names
    storage_id = f"{uuid.uuid4().hex}.{file_ext}"
    
    # Secure Temporary Storage for Processing
    file_path = os.path.join(UPLOAD_DIR, storage_id)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(document_image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not save temporary file.")
    
    # 2. Database Initialization (Pending State)
    db_scan = Scan(
        session_id=session_id, 
        status="PROCESSING",
        document_content_type=document_image.content_type,
        document_file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0
    )
    try:
        db.add(db_scan)
        await log_audit_event(db, "SCAN_CREATED", scan_id=session_id, event_metadata={"doc_type": "UNKNOWN"})
        await log_audit_event(db, "DOCUMENT_UPLOADED", scan_id=session_id, event_metadata={"file_size": db_scan.document_file_size})
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Database connection failed during initialization: {str(e)}")
        db_scan = None
        
    # 3. Execute pipeline with the real file path
    try:
        result = execute_scan_pipeline(session_id, file_path)
        
        await log_audit_event(db, "AI_ANALYSIS_COMPLETED", scan_id=session_id)
        await log_audit_event(db, "RISK_ASSESSMENT_COMPLETED", scan_id=session_id, event_metadata={
            "risk_level": result["risk_decision"]["risk_level"]
        })
        
        # 4. Storage Retention
        if settings.DOCUMENT_RETENTION_ENABLED and db_scan is not None:
            storage_service = get_storage_service()
            with open(file_path, "rb") as f:
                saved_id = await storage_service.save(storage_id, f)
            db_scan.document_storage_id = saved_id
            await log_audit_event(db, "DOCUMENT_PROCESSED", scan_id=session_id, event_metadata={"action": "retained"})
        else:
            await log_audit_event(db, "DOCUMENT_PROCESSED", scan_id=session_id, event_metadata={"action": "discarded"})

    finally:
        # Clean up the temporary file ALWAYS
        if os.path.exists(file_path):
            os.remove(file_path)
            
    # 3. Database Persistence (Completion State)
    if db_scan is not None:
        try:
            # Re-fetch or directly update
            db_scan.status = "COMPLETED"
            db_scan.risk_level = result["risk_decision"]["risk_level"]
            db_scan.numerical_score = result["risk_decision"]["numerical_score"]
            db_scan.explanation = result["risk_decision"]["explanation"]
            db_scan.mrz_status = result["pipeline_data"].get("mrz_status", "UNKNOWN")
            db_scan.tampering_status = result["pipeline_data"].get("tampering_status", "UNKNOWN")
            db_scan.face_status = result["pipeline_data"].get("face_status", "UNKNOWN")
            
            await db.commit()
            await db.refresh(db_scan)
        except Exception as e:
            await db.rollback()
            logger.error(f"Database connection failed during persistence: {str(e)}")
            
    return result

from app.api.deps import require_role
from app.models.user import User

class VerificationDecisionRequest(BaseModel):
    notes: Optional[str] = None

@router.post("/verification/{scan_id}/approve")
async def approve_scan(scan_id: str, request: Optional[VerificationDecisionRequest] = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role(["ADMIN", "OFFICER"]))):
    return await handle_verification_decision(scan_id, "APPROVED", db, current_user, request.notes if request else None)

@router.post("/verification/{scan_id}/escalate")
async def escalate_scan(scan_id: str, request: Optional[VerificationDecisionRequest] = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role(["ADMIN", "OFFICER"]))):
    return await handle_verification_decision(scan_id, "ESCALATED", db, current_user, request.notes if request else None)

@router.post("/verification/{scan_id}/reject")
async def reject_scan(scan_id: str, request: Optional[VerificationDecisionRequest] = None, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role(["ADMIN", "OFFICER"]))):
    return await handle_verification_decision(scan_id, "REJECTED", db, current_user, request.notes if request else None)

from datetime import datetime, timezone

async def handle_verification_decision(scan_id: str, decision: str, db: AsyncSession, current_user: User, notes: Optional[str] = None):
    # Retrieve the scan
    result = await db.execute(select(Scan).where(Scan.session_id == scan_id))
    db_scan = result.scalars().first()
    
    if not db_scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    if db_scan.human_verification_status in ["APPROVED", "REJECTED", "ESCALATED"]:
        raise HTTPException(status_code=400, detail=f"Scan already processed with decision: {db_scan.human_verification_status}")
        
    db_scan.human_verification_status = decision
    db_scan.human_decision = decision
    db_scan.human_decision_at = datetime.now(timezone.utc)
    db_scan.human_reviewer_id = current_user.id
    
    event_type = f"SCAN_{decision}"
    await log_audit_event(
        db=db,
        event_type=event_type,
        scan_id=scan_id,
        actor_user_id=current_user.id,
        event_metadata={"notes": notes} if notes else {}
    )
    
    try:
        await db.commit()
        await db.refresh(db_scan)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    return {
        "status": "success",
        "session_id": scan_id,
        "human_verification_status": db_scan.human_verification_status,
        "human_decision_at": db_scan.human_decision_at
    }

from app.models.audit import AuditLog

@router.get("/scans/{scan_id}/audit")
async def get_scan_audit_history(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "OFFICER", "REVIEWER"]))
):
    result = await db.execute(select(AuditLog).where(AuditLog.scan_id == scan_id).order_by(AuditLog.timestamp.asc()))
    events = result.scalars().all()
    
    formatted_events = []
    for event in events:
        formatted_events.append({
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "actor": event.actor_user_id,
            "status": event.event_status,
            "metadata": event.event_metadata
        })
        
    return {
        "scan_id": scan_id,
        "events": formatted_events
    }

@router.get("/scans/{scan_id}/document")
async def get_scan_document(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "OFFICER", "REVIEWER"]))
):
    """
    Secure backend proxy for retrieving retained document images.
    """
    result = await db.execute(select(Scan).where(Scan.session_id == scan_id))
    db_scan = result.scalars().first()
    
    if not db_scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    if not db_scan.document_storage_id:
        raise HTTPException(status_code=404, detail="No document retained for this scan")
        
    storage_service = get_storage_service()
    if not await storage_service.exists(db_scan.document_storage_id):
        raise HTTPException(status_code=404, detail="Document missing from storage")
        
    file_path = await storage_service.get(db_scan.document_storage_id)
    if file_path:
        # Note: In Azure, this might be a SAS URL redirect, but for local:
        return FileResponse(file_path, media_type=db_scan.document_content_type)
    
    raise HTTPException(status_code=500, detail="Failed to retrieve document")
