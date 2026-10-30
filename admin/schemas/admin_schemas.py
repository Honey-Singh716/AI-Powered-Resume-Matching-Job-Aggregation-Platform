"""
All Pydantic schemas for admin API responses.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ─── Dashboard ────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    total_users: int
    verified_users: int
    unverified_users: int
    candidates: int
    recruiters: int
    admins: int
    total_jobs: int
    jobs_by_source: dict
    total_applications: int
    candidates_with_resumes: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int


class UserRegistrationPoint(BaseModel):
    date: str
    count: int


class DashboardCharts(BaseModel):
    user_registrations: List[UserRegistrationPoint]
    jobs_by_source: dict
    role_distribution: dict
    verification_distribution: dict


# ─── Users ────────────────────────────────────────────────────

class AdminUserItem(BaseModel):
    id: int
    email: str
    role: str
    is_verified: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminUserDetail(BaseModel):
    id: int
    email: str
    role: str
    is_verified: bool
    created_at: Optional[datetime] = None
    has_candidate_profile: bool = False
    application_count: int = 0

    class Config:
        from_attributes = True


class AdminUsersResponse(BaseModel):
    users: List[AdminUserItem]
    total: int
    skip: int
    limit: int


# ─── Jobs ─────────────────────────────────────────────────────

class AdminJobItem(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str] = None
    source: str
    employment_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class AdminJobsResponse(BaseModel):
    jobs: List[AdminJobItem]
    total: int
    skip: int
    limit: int


class JobStats(BaseModel):
    total_jobs: int
    by_source: dict
    internal_jobs: int
    aggregated_jobs: int


# ─── System Health ────────────────────────────────────────────

class ServiceHealth(BaseModel):
    name: str
    status: str          # "healthy", "warning", "unhealthy", "unknown"
    response_ms: Optional[float] = None
    message: Optional[str] = None
    last_checked: datetime


class SystemHealthResponse(BaseModel):
    services: List[ServiceHealth]
    overall_status: str


# ─── Audit Logs ───────────────────────────────────────────────

class AuditLogItem(BaseModel):
    id: int
    admin_user_id: int
    admin_email: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    description: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogsResponse(BaseModel):
    logs: List[AuditLogItem]
    total: int
    skip: int
    limit: int


# ─── Email / OTP Stats ────────────────────────────────────────

class EmailOTPStats(BaseModel):
    total_users: int
    verified_users: int
    unverified_users: int
    verification_rate_pct: float
    users_with_pending_otp: int
    recently_verified: List[dict]
