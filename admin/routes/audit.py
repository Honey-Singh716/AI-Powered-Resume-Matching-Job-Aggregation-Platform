"""
Admin Audit Log routes.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from admin.utils.permissions import require_admin
from admin.services.audit_service import list_audit_logs

router = APIRouter()


@router.get("/audit-logs")
def admin_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin_user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Paginated admin audit log with optional filters."""
    return list_audit_logs(db, skip, limit, admin_user_id, action)
