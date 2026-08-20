from fastapi import HTTPException

# Use the extended repository with verification helpers
from repositories.user_repo_ext import create_user, get_user_by_email, set_verification_token
from services.auth_service import hash_password,verify_password,create_access_token
from services.email_service import send_verification_email

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import os


def save_user(user_data,db):

    email = user_data.email
    existing_user = get_user_by_email(email,db)
    
    if existing_user:
        raise  HTTPException(status_code=400, detail="User with this email already exists")
 

    password = user_data.password
    hashed_password = hash_password(password)
    role = user_data.role

    # Create user (unverified by default)
    user = create_user(email,hashed_password,role,db)

    # Generate secure token and store only its SHA-256 hash
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    sent_at = datetime.now(timezone.utc)

    # Persist hashed token and timestamps
    set_verification_token(user, token_hash, expires_at, sent_at, db)

    # Send verification email via email service
    try:
        send_verification_email(user.email, raw_token, expires_at)
    except Exception as e:
        # Do not leak secrets or token; surface a generic error
        raise HTTPException(status_code=500, detail="Failed to send verification email")

    return user


def login_user(login_data,db):

    user = get_user_by_email(login_data.email,db)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    

    if not verify_password(login_data.password,user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    

    # Block unverified users from obtaining a token
    if not getattr(user, 'is_verified', False):
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    token = create_access_token({
        "sub" : user.email,
        "role": user.role
    })

    return {
        "access_token":token,
        "token_type" : "bearer"
    }