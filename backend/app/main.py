import subprocess
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.core.config import settings

app = FastAPI(
    title="TRUSTSCAN API",
    description="AI-Powered Identity & Document Verification System",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.auth import router as auth_router

app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
@app.get("/")
def root():
    return {"message": "Welcome to TRUSTSCAN API"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/system/health")
def health_check():
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "modules": {}
    }
    
    # Check OCR (Tesseract)
    try:
        # In a real environment we might use pytesseract.get_tesseract_version()
        # For this check, we verify the binary exists and responds
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
        health_status["modules"]["ocr_engine"] = "operational"
    except Exception as e:
        health_status["modules"]["ocr_engine"] = f"failed: {str(e)}"
        health_status["status"] = "degraded"
        
    # Check AI Models (Verify the real functions can be imported)
    try:
        from app.services.tamper_service import analyze_image
        health_status["modules"]["tamper_engine"] = "operational"
    except Exception as e:
        health_status["modules"]["tamper_engine"] = "failed"
        health_status["status"] = "degraded"
        
    try:
        from app.services.face_service import verify_faces
        health_status["modules"]["face_engine"] = "operational"
    except Exception as e:
        health_status["modules"]["face_engine"] = "failed"
        health_status["status"] = "degraded"

    if health_status["status"] == "degraded":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
        
    return health_status
