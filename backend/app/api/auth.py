from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.audit_service import log_audit_event

router = APIRouter()

@router.post("/login/access-token")
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        await log_audit_event(
            db=db,
            event_type="AUTH_LOGIN_FAILURE",
            event_status="FAILURE",
            event_metadata={"username": form_data.username, "reason": "Incorrect credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password"
        )
    elif not user.is_active:
        await log_audit_event(
            db=db,
            event_type="AUTH_LOGIN_FAILURE",
            event_status="FAILURE",
            event_metadata={"username": form_data.username, "reason": "Inactive user"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
        
    await log_audit_event(
        db=db,
        event_type="AUTH_LOGIN_SUCCESS",
        actor_user_id=user.id,
        event_metadata={"username": user.username}
    )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
