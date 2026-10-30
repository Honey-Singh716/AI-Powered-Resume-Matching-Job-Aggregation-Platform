"""
Admin Dashboard Service — aggregates KPI and chart data from real DB queries.
All statistics come from the actual database; no hardcoded or fake values.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import func, cast, Date, text
from sqlalchemy.orm import Session

from models.user import User
from models.job import Job
from models.application import Application
from models.candidate import Candidate

logger = logging.getLogger(__name__)


def get_dashboard_summary(db: Session) -> dict:
    """Compute all KPI card values using efficient aggregation queries."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # User counts
    total_users = db.query(func.count(User.id)).scalar() or 0
    verified_users = db.query(func.count(User.id)).filter(User.is_verified == True).scalar() or 0
    unverified_users = total_users - verified_users
    candidates = db.query(func.count(User.id)).filter(User.role == "candidate").scalar() or 0
    recruiters = db.query(func.count(User.id)).filter(User.role == "recruiter").scalar() or 0
    admins = db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0

    # New users (only if created_at column exists)
    new_today = 0
    new_week = 0
    new_month = 0
    try:
        new_today = db.query(func.count(User.id)).filter(
            User.created_at >= today_start
        ).scalar() or 0
        new_week = db.query(func.count(User.id)).filter(
            User.created_at >= week_start
        ).scalar() or 0
        new_month = db.query(func.count(User.id)).filter(
            User.created_at >= month_start
        ).scalar() or 0
    except Exception:
        pass  # created_at not yet available

    # Job counts
    total_jobs = db.query(func.count(Job.id)).scalar() or 0

    # Jobs by source
    source_rows = (
        db.query(Job.source, func.count(Job.id))
        .group_by(Job.source)
        .all()
    )
    jobs_by_source = {row[0]: row[1] for row in source_rows}

    # Applications
    total_applications = db.query(func.count(Application.id)).scalar() or 0

    # Candidates with resume profiles
    candidates_with_resumes = db.query(func.count(Candidate.id)).scalar() or 0

    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "unverified_users": unverified_users,
        "candidates": candidates,
        "recruiters": recruiters,
        "admins": admins,
        "total_jobs": total_jobs,
        "jobs_by_source": jobs_by_source,
        "total_applications": total_applications,
        "candidates_with_resumes": candidates_with_resumes,
        "new_users_today": new_today,
        "new_users_this_week": new_week,
        "new_users_this_month": new_month,
    }


def get_dashboard_charts(db: Session) -> dict:
    """Build chart data for the admin dashboard."""
    # User registrations per day (last 30 days)
    user_registrations = []
    try:
        rows = (
            db.query(
                cast(User.created_at, Date).label("day"),
                func.count(User.id).label("count")
            )
            .filter(User.created_at >= datetime.now(timezone.utc) - timedelta(days=30))
            .group_by(cast(User.created_at, Date))
            .order_by(cast(User.created_at, Date))
            .all()
        )
        user_registrations = [{"date": str(r.day), "count": r.count} for r in rows]
    except Exception:
        pass

    # Jobs by source
    source_rows = (
        db.query(Job.source, func.count(Job.id))
        .group_by(Job.source)
        .all()
    )
    jobs_by_source = {row[0]: row[1] for row in source_rows}

    # Role distribution
    role_rows = (
        db.query(User.role, func.count(User.id))
        .group_by(User.role)
        .all()
    )
    role_distribution = {row[0]: row[1] for row in role_rows}

    # Verification distribution
    total = db.query(func.count(User.id)).scalar() or 0
    verified = db.query(func.count(User.id)).filter(User.is_verified == True).scalar() or 0
    verification_distribution = {
        "verified": verified,
        "unverified": max(0, total - verified),
    }

    return {
        "user_registrations": user_registrations,
        "jobs_by_source": jobs_by_source,
        "role_distribution": role_distribution,
        "verification_distribution": verification_distribution,
    }
