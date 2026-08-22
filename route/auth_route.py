import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import hashlib

from database import get_db

from schemas.user import UserLogin
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


@router.get('/verify-email')
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify an email using the raw token supplied in the URL query.

    Steps:
      - Hash the token
      - Find user by token hash
      - Check expiry
      - Mark verified and clear token fields
    """
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    user = get_user_by_verification_hash(token_hash, db)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    now = datetime.now(timezone.utc)
    if not user.verification_token_expires_at or user.verification_token_expires_at < now:
        raise HTTPException(status_code=400, detail="Token has expired")

    # Mark verified and clear token fields
    user.is_verified = True
    clear_verification_token(user, db)

    # Redirect or return success; keep it simple and return JSON indicating success
    return {"detail": "Email verified successfully"}


@router.post('/resend-verification')
def resend_verification(request: dict, db: Session = Depends(get_db)):
    """Resend verification email. To avoid account enumeration, always return a generic success message.

    Expects JSON: {"email":"user@example.com"}
    """
    email = request.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Cooldown in seconds (e.g., 5 minutes)
    COOLDOWN_SECONDS = 300

    user = get_user_by_email(email, db)

    # If no user or already verified: return generic success message (avoid enumeration)
    generic_resp = {"detail": "If an account exists, a verification email has been sent."}

    if not user:
        return generic_resp

    if getattr(user, 'is_verified', False):
        return generic_resp

    # Rate limit: check last sent timestamp
    now = datetime.now(timezone.utc)
    if user.verification_token_sent_at and (now - user.verification_token_sent_at).total_seconds() < COOLDOWN_SECONDS:
        # Return generic message but with 429 to indicate rate limiting
        raise HTTPException(status_code=429, detail="Too many requests — try again later")

    # Generate a new token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = now + timedelta(minutes=30)
    sent_at = now

    set_verification_token(user, token_hash, expires_at, sent_at, db)

    try:
        send_verification_email(user.email, raw_token, expires_at)
    except Exception:
        logging.exception("Failed to resend verification email for %s", user.email)
        raise HTTPException(
            status_code=500,
            detail="Failed to send verification email. Check your Resend API key and verified sender email."
        )

    return generic_resp