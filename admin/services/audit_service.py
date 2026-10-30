"""
Admin Audit Service — records and retrieves admin audit log entries.
"""
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.audit_log import AdminAuditLog
from models.user import User

logger = logging.getLogger(__name__)


def create_audit_log(
    db: Session,
    admin_user_id: int,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    description: Optional[str] = None,
    status: str = "success",
) -> AdminAuditLog:
    """Create a new audit log entry."""
    log = AdminAuditLog(
        admin_user_id=admin_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        status=status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_audit_logs(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    admin_user_id: Optional[int] = None,
    action: Optional[str] = None,
) -> dict:
    """Return paginated audit logs with optional filters."""
    query = db.query(AdminAuditLog)

    if admin_user_id:
        query = query.filter(AdminAuditLog.admin_user_id == admin_user_id)
    if action:
        query = query.filter(AdminAuditLog.action.ilike(f"%{action}%"))

    total = query.count()
    logs_raw = (
        query.order_by(AdminAuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Enrich with admin email
    logs = []
    for log in logs_raw:
        admin = db.query(User).filter(User.id == log.admin_user_id).first()
        logs.append({
            "id": log.id,
            "admin_user_id": log.admin_user_id,
            "admin_email": admin.email if admin else "Unknown",
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "description": log.description,
            "status": log.status,
            "created_at": log.created_at,
        })

    return {"logs": logs, "total": total, "skip": skip, "limit": limit}
