"""
Admin User Management routes.
NEVER exposes: passwords, OTP hashes, JWT tokens, or secrets.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from admin.utils.permissions import require_admin
from admin.services import user_service, audit_service

router = APIRouter()


@router.get("/users")
def admin_list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_verified: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Paginated user list with search and filters."""
    return user_service.list_users(db, skip, limit, search, role, is_verified)


@router.get("/users/{user_id}")
def admin_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """User detail — safe fields only."""
    detail = user_service.get_user_detail(user_id, db)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")

    audit_service.create_audit_log(
        db, admin.id, "VIEW_USER", "user", str(user_id),
        f"Viewed user {detail['email']}"
    )
    return detail


@router.patch("/users/{user_id}/toggle-verification")
def admin_toggle_user_verification(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Toggle a user's email verification status."""
    user = user_service.toggle_user_verification(user_id, db, admin.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    action = "VERIFY_USER" if user.is_verified else "UNVERIFY_USER"
    audit_service.create_audit_log(
        db, admin.id, action, "user", str(user_id),
        f"Toggled verification for {user.email} → {user.is_verified}"
    )
    return {"id": user.id, "email": user.email, "is_verified": user.is_verified}


@router.delete("/users/{user_id}")
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Delete a user account."""
    # Prevent admin from deleting themselves
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own admin account.")

    # Get email before deleting for audit log
    detail = user_service.get_user_detail(user_id, db)
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")

    deleted = user_service.delete_user(user_id, db, admin.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")

    audit_service.create_audit_log(
        db, admin.id, "DELETE_USER", "user", str(user_id),
        f"Deleted user {detail['email']}"
    )
    return {"detail": f"User {detail['email']} deleted successfully."}
