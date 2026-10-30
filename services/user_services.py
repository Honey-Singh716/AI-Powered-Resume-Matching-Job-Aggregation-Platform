import logging
from fastapi import HTTPException

from repositories.user_repo_ext import (
    create_user,
    get_user_by_email,
    set_verification_token
)

from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token
)

from services.email_service import send_verification_email

import secrets
import hashlib
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# OTP verification enabled
EMAIL_VERIFICATION_ENABLED = True


def save_user(user_data, db):

    email = user_data.email

    existing_user = get_user_by_email(email, db)

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )

    password = user_data.password
    hashed_password = hash_password(password)
    role = user_data.role

    # Create user
    user = create_user(
        email,
        hashed_password,
        role,
        db
    )

    if EMAIL_VERIFICATION_ENABLED:

        # -----------------------------------------
        # Generate secure 6-digit OTP
        # -----------------------------------------

        otp = f"{secrets.randbelow(1_000_000):06d}"

        # Store only hash of OTP
        otp_hash = hashlib.sha256(
            otp.encode()
        ).hexdigest()

        # OTP valid for 5 minutes
        now = datetime.now(timezone.utc)

        expires_at = now + timedelta(minutes=5)

        set_verification_token(
            user,
            otp_hash,
            expires_at,
            now,
            db
        )

        try:

            # Send OTP through n8n
            send_verification_email(
                user.email,
                otp,
                expires_at
            )

        except Exception:

            logger.exception(
                "Failed to send OTP email for %s",
                user.email
            )

            return {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "detail": "Account created, but OTP email could not be sent.",
                "verification_email_sent": False,
            }

        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "detail": "Account created. OTP sent to your email.",
            "verification_email_sent": True,
            "verified": False
        }

    # Should not normally be used now
    user.is_verified = True
    db.commit()

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "detail": "Account created successfully.",
        "verification_email_sent": False,
        "verified": True
    }


def login_user(login_data, db):

    user = get_user_by_email(
        login_data.email,
        db
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        login_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Email MUST be verified
    if EMAIL_VERIFICATION_ENABLED:

        if not getattr(user, "is_verified", False):

            raise HTTPException(
                status_code=403,
                detail="Please verify your email before logging in."
            )

    token = create_access_token({
        "sub": user.email,
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }