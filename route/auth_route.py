import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import hashlib

from database import get_db

from schemas.user import UserLogin, OTPVerify
from services.user_services import login_user

# Use extended repository for verification helpers
from repositories.user_repo_ext import get_user_by_email, get_user_by_verification_hash, set_verification_token, clear_verification_token
from services.email_service import send_verification_email

import secrets
import os

router = APIRouter(
    prefix="/auth",
    tags=['Authentication']
)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):

    # OAuth2 form sends 'username' — we treat it as email
    from types import SimpleNamespace
    login_data = SimpleNamespace(email=form_data.username, password=form_data.password)
    return login_user(login_data,db)


@router.post('/verify-email')
def verify_email(payload: OTPVerify, db: Session = Depends(get_db)):
    """Verify an email using OTP."""
    user = get_user_by_email(payload.email, db)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid request")

    if getattr(user, 'is_verified', False):
        return {"detail": "Email already verified"}

    token_hash = hashlib.sha256(payload.otp.encode()).hexdigest()

    if user.verification_token_hash != token_hash:
        raise HTTPException(status_code=400, detail="Invalid OTP. Please try again.")

    now = datetime.now(timezone.utc)
    if not user.verification_token_expires_at or user.verification_token_expires_at < now:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new OTP.")

    # Mark verified and clear token fields
    user.is_verified = True
    clear_verification_token(user, db)

    return {"detail": "Email verified successfully."}