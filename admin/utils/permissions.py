"""
Admin permission utilities.
Provides a FastAPI dependency that enforces admin-only access.
The role check is performed on the backend from the JWT token —
frontend cannot bypass this.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db

from services.auth_service import current_user


def require_admin(user=Depends(current_user)):
    """
    FastAPI dependency: verifies the authenticated user has role='admin'.
    Returns the user object if admin, raises HTTP 403 otherwise.
    """
    if getattr(user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. You do not have permission to access this resource.",
        )
    return user
