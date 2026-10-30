"""
Admin User Service — manages admin-level user operations.
Never exposes passwords, OTP hashes, or secrets.
"""
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.user import User
from models.candidate import Candidate
from models.application import Application

logger = logging.getLogger(__name__)


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_verified: Optional[bool] = None,
) -> dict:
    """Return paginated user list. Safe fields only — no passwords or OTP hashes."""
    query = db.query(User)

    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))
    if role:
        query = query.filter(User.role == role)
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)

    total = query.count()
    users = (
        query.order_by(User.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


def get_user_detail(user_id: int, db: Session) -> Optional[dict]:
    """Return safe user detail including profile and application stats."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    has_candidate_profile = (
        db.query(Candidate).filter(Candidate.user_id == user_id).first() is not None
    )

    application_count = 0
    if has_candidate_profile:
        candidate = db.query(Candidate).filter(Candidate.user_id == user_id).first()
        if candidate:
            application_count = (
                db.query(func.count(Application.id))
                .filter(Application.candidate_id == candidate.id)
                .scalar() or 0
            )

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified,
        "created_at": getattr(user, "created_at", None),
        "has_candidate_profile": has_candidate_profile,
        "application_count": application_count,
    }


def toggle_user_verification(user_id: int, db: Session, admin_id: int) -> Optional[User]:
    """Toggle a user's is_verified status. Returns the updated user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    user.is_verified = not user.is_verified
    db.commit()
    db.refresh(user)
    logger.info("Admin %s toggled verification for user %s → %s", admin_id, user_id, user.is_verified)
    return user


def delete_user(user_id: int, db: Session, admin_id: int) -> bool:
    """Delete a user by ID. Returns True if deleted, False if not found."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    db.delete(user)
    db.commit()
    logger.info("Admin %s deleted user %s (%s)", admin_id, user_id, user.email)
    return True
