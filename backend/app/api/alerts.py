"""Expiry alerts API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import ExpiryAlertResponse
from app.services import alert_service

router = APIRouter(prefix="/api", tags=["Alerts"])


@router.get(
    "/alerts/expiry",
    response_model=ExpiryAlertResponse,
    summary="Get expiry alerts",
)
def get_expiry_alerts(
    days: int = Query(30, ge=1, le=365, description="Alert threshold in days"),
    db: Session = Depends(get_db),
):
    """
    Returns batches that are expired or expiring within the specified
    number of days. Results are sorted by urgency.

    Categories:
    - EXPIRED: expiry_date < today
    - CRITICAL: 0-7 days remaining
    - EXPIRING_SOON: 8-30 days remaining
    - HEALTHY: >30 days remaining
    """
    return alert_service.get_expiry_alerts(db, threshold_days=days)
