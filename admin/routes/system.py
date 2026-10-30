"""
Admin System Health routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from admin.utils.permissions import require_admin
from admin.services.system_service import get_system_health

router = APIRouter()


@router.get("/system/health")
def admin_system_health(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Real-time service health status — PostgreSQL, Redis, n8n, AI, Embedding model."""
    return get_system_health(db)


@router.get("/system/email-otp-stats")
def admin_email_otp_stats(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """
    Email / OTP verification statistics.
    Safe metadata only — NO OTP values, hashes, or email credentials.
    """
    from models.user import User
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta

    total = db.query(func.count(User.id)).scalar() or 0
    verified = db.query(func.count(User.id)).filter(User.is_verified == True).scalar() or 0
    unverified = total - verified

    # Users currently holding a pending OTP token (not yet verified)
    pending_otp = (
        db.query(func.count(User.id))
        .filter(
            User.is_verified == False,
            User.verification_token_hash != None,
            User.verification_token_expires_at > datetime.now(timezone.utc),
        )
        .scalar() or 0
    )

    rate = round((verified / total * 100), 1) if total > 0 else 0.0

    # Recent verifications — show email and verification time, NO OTP data
    recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_users = (
        db.query(User.email, User.verification_token_sent_at)
        .filter(User.is_verified == True)
        .order_by(User.id.desc())
        .limit(10)
        .all()
    )
    recently_verified = [
        {"email": u.email, "verified_at": str(u.verification_token_sent_at) if u.verification_token_sent_at else "N/A"}
        for u in recent_users
    ]

    return {
        "total_users": total,
        "verified_users": verified,
        "unverified_users": unverified,
        "verification_rate_pct": rate,
        "users_with_pending_otp": pending_otp,
        "recently_verified": recently_verified,
    }
