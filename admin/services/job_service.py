"""
Admin Job Service — job monitoring and management.
"""
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, defer

from models.job import Job

logger = logging.getLogger(__name__)


def list_jobs(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """Return paginated job list for admin view."""
    query = db.query(Job).options(defer(Job.embedding))

    if search:
        query = query.filter(
            Job.title.ilike(f"%{search}%") |
            Job.company.ilike(f"%{search}%") |
            Job.location.ilike(f"%{search}%")
        )
    if source:
        query = query.filter(Job.source == source)

    total = query.count()
    jobs = (
        query.order_by(Job.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {"jobs": jobs, "total": total, "skip": skip, "limit": limit}


def get_job_stats(db: Session) -> dict:
    """Compute job statistics by source."""
    total_jobs = db.query(func.count(Job.id)).scalar() or 0

    source_rows = (
        db.query(Job.source, func.count(Job.id))
        .group_by(Job.source)
        .all()
    )
    by_source = {row[0]: row[1] for row in source_rows}

    internal_jobs = by_source.get("internal", 0)
    aggregated_jobs = total_jobs - internal_jobs

    return {
        "total_jobs": total_jobs,
        "by_source": by_source,
        "internal_jobs": internal_jobs,
        "aggregated_jobs": aggregated_jobs,
    }


def delete_job(job_id: int, db: Session, admin_id: int) -> bool:
    """Delete a job by ID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return False
    db.delete(job)
    db.commit()
    logger.info("Admin %s deleted job %s (%s)", admin_id, job_id, job.title)
    return True
