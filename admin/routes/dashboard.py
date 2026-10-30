"""
Admin Dashboard routes — KPI summary and chart data.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from admin.utils.permissions import require_admin
from admin.services.dashboard_service import get_dashboard_summary, get_dashboard_charts

router = APIRouter()


@router.get("/dashboard/summary")
def admin_dashboard_summary(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """KPI card data — real counts from database. No hardcoded values."""
    return get_dashboard_summary(db)


@router.get("/dashboard/charts")
def admin_dashboard_charts(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Chart data — user registrations over time, jobs by source, distributions."""
    return get_dashboard_charts(db)
