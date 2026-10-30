"""
Admin master router — aggregates all admin sub-routers under /admin prefix.
"""
from fastapi import APIRouter
from admin.routes import dashboard, users, jobs, system, audit

router = APIRouter(prefix="/admin", tags=["Admin"])

router.include_router(dashboard.router)
router.include_router(users.router)
router.include_router(jobs.router)
router.include_router(system.router)
router.include_router(audit.router)
