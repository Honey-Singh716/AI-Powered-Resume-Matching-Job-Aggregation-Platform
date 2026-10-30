"""
Admin API Routes — all endpoints are protected by require_admin dependency.
Prefix: /admin
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from admin.utils.permissions import require_admin
from admin.schemas.admin_schemas import (
    DashboardSummary,
    DashboardCharts,
    AdminUsersResponse,
    AdminUserDetail,
    AdminUserItem,
    AdminJobsResponse,
    JobStats,
    SystemHealthResponse,
    AuditLogsResponse,
)
from admin.services import (
    dashboard_service,
    user_service,
    job_service,
    system_service,
    audit_service,
)
from models.audit_log import AdminAuditLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# ─────────────────────────────── Dashboard ───────────────────────────────────

@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """KPI summary cards for the admin dashboard."""
    return dashboard_service.get_dashboard_summary(db)


@router.get("/dashboard/charts", response_model=DashboardCharts)
def dashboard_charts(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Chart data (user growth, job sources, role distribution)."""
    return dashboard_service.get_dashboard_charts(db)


# ─────────────────────────────── Users ───────────────────────────────────────

@router.get("/users", response_model=AdminUsersResponse)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_verified: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Paginated user list with optional filters."""
    result = user_service.list_users(db, skip, limit, search, role, is_verified)
    return result


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Detailed user record including profile and application stats."""
    detail = user_service.get_user_detail(user_id, db)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")
    return detail


@router.post("/users/{user_id}/toggle-verification", response_model=AdminUserItem)
def toggle_verification(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Toggle email verification status for a user."""
    user = user_service.toggle_user_verification(user_id, db, admin.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Write audit log
    audit_service.create_audit_log(
        db,
        admin_user_id=admin.id,
        action="toggle_verification",
        resource_type="user",
        resource_id=str(user_id),
        description=f"Verification toggled → {user.is_verified}",
    )
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Permanently delete a user account."""
    deleted = user_service.delete_user(user_id, db, admin.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    audit_service.create_audit_log(
        db,
        admin_user_id=admin.id,
        action="delete_user",
        resource_type="user",
        resource_id=str(user_id),
        description="User account deleted by admin",
    )


# ─────────────────────────────── Jobs ────────────────────────────────────────

@router.get("/jobs", response_model=AdminJobsResponse)
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Paginated job list with optional search/source filter."""
    return job_service.list_jobs(db, skip, limit, search, source)


@router.get("/jobs/stats", response_model=JobStats)
def job_stats(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Aggregated job statistics by source."""
    return job_service.get_job_stats(db)


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Delete a job listing."""
    deleted = job_service.delete_job(job_id, db, admin.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    audit_service.create_audit_log(
        db,
        admin_user_id=admin.id,
        action="delete_job",
        resource_type="job",
        resource_id=str(job_id),
        description="Job deleted by admin",
    )


# ─────────────────────────────── System Health ───────────────────────────────

@router.get("/system/health", response_model=SystemHealthResponse)
def system_health(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Real-time health status of all connected services."""
    return system_service.get_system_health(db)


# ─────────────────────────────── Audit Logs ──────────────────────────────────

@router.get("/audit-logs", response_model=AuditLogsResponse)
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin_user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Paginated admin audit log with optional filters."""
    return audit_service.list_audit_logs(db, skip, limit, admin_user_id, action)
