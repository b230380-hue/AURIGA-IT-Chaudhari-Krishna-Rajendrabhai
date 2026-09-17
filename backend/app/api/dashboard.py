"""Dashboard API route."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard_service

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get pharmacy dashboard data",
)
def get_dashboard(db: Session = Depends(get_db)):
    """
    Returns comprehensive dashboard data including:
    - Summary cards (sellable, expired, expiring-soon units)
    - Inventory health score (deterministic, transparent)
    - Expiry exposure (stock at risk)
    - Batches needing attention
    - FEFO queue (next batches to dispense)
    - Recent dispensing transactions
    """
    return dashboard_service.get_dashboard(db)
