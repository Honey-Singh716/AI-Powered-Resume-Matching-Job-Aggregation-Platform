import logging
from fastapi import HTTPException

# Use the extended repository with verification helpers
from repositories.user_repo_ext import create_user, get_user_by_email, set_verification_token
from services.auth_service import hash_password,verify_password,create_access_token
from services.email_service import send_verification_email

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------
# TODO: Set this to True once you have a verified email domain
#       and a working RESEND_API_KEY configured in .env
# ---------------------------------------------------------------
EMAIL_VERIFICATION_ENABLED = False


def save_user(user_data, db):

    email = user_data.email
    existing_user = get_user_by_email(email, db)

    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    password = user_data.password
    hashed_password = hash_password(password)
    role = user_data.role

    # Create user — is_verified starts as False in DB
    user = create_user(email, hashed_password, role, db)

    if EMAIL_VERIFICATION_ENABLED:
        # --- Email verification pipeline (enable when domain is ready) ---
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        sent_at = datetime.now(timezone.utc)

        set_verification_token(user, token_hash, expires_at, sent_at, db)

        try:
            send_verification_email(user.email, raw_token, expires_at)
        except Exception:
            logger.exception("Failed to send verification email during signup for %s", user.email)
            return {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "detail": "Account created, but verification email could not be sent right now. Please try resending the verification email later.",
                "verification_email_sent": False,
            }

        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "detail": "Account created. Verification email sent.",
            "verification_email_sent": True,
        }
    else:
        # --- Bypass: auto-verify the user so they can login immediately ---
        user.is_verified = True
        db.commit()
        logger.info("Email verification bypassed for %s (EMAIL_VERIFICATION_ENABLED=False)", user.email)
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "detail": "Account created successfully! You can now sign in.",
            "verification_email_sent": False,
            "verified": True,
        }


def login_user(login_data, db):

    user = get_user_by_email(login_data.email, db)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if EMAIL_VERIFICATION_ENABLED:
        # Block unverified users only when verification is active
        if not getattr(user, 'is_verified', False):
            raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    token = create_access_token({
        "sub": user.email,
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }