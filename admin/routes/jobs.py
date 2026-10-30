"""
Admin Job Management routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from admin.utils.permissions import require_admin
from admin.services import job_service, audit_service

router = APIRouter()


@router.get("/jobs")
def admin_list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Paginated job list with search and source filter."""
    return job_service.list_jobs(db, skip, limit, search, source)


@router.get("/jobs/stats")
def admin_job_stats(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Job statistics: total, by source, internal vs aggregated."""
    return job_service.get_job_stats(db)


@router.delete("/jobs/{job_id}")
def admin_delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Delete a job listing."""
    deleted = job_service.delete_job(job_id, db, admin.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")

    audit_service.create_audit_log(
        db, admin.id, "DELETE_JOB", "job", str(job_id),
        f"Deleted job ID {job_id}"
    )
    return {"detail": f"Job {job_id} deleted successfully."}
