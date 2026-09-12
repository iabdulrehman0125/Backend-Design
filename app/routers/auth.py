import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, PasswordResetToken
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.security import verify_password, create_access_token
from app.deps import get_current_user
from datetime import datetime, timedelta

n

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    # Always return the same message — don't reveal whether the email exists
    if not user:
        return {"message": "If that email exists, we sent a reset link."}

    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)

    db.add(PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires,
    ))
    db.commit()

    # TODO: send email with reset link:
    # f"https://frontend-design-sable.vercel.app/reset-password?token={token}"

    return {"message": "If that email exists, we sent a reset link."}