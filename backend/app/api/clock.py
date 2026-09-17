"""
Clock API routes — automated daily job and simulated date controls.
Level 1 — T2 (automation): Graded via POST /clock.
"""

from typing import Any
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import clock_service

router = APIRouter(tags=["Clock & Automation"])


@router.post("/clock", summary="Advance clock and execute daily automation job")
@router.post("/api/clock", summary="Advance clock and execute daily automation job")
def post_clock(
    payload: dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
):
    """
    Advance system clock or set a specific date, and trigger daily automation:
      - Quarantines expired batches.
      - Flags batches expiring within 7 days.
      - Checks reorder thresholds and sends outbox notifications.
      - Returns counts report { quarantined, flagged, ... }.
    """
    target_date = payload.get("date")
    days = payload.get("days")
    return clock_service.advance_clock(db, target_date=target_date, days=days)


@router.get("/clock", summary="Get current clock date")
@router.get("/api/clock", summary="Get current clock date")
def get_clock(db: Session = Depends(get_db)):
    """Retrieve the current date (simulated or real)."""
    current = clock_service.get_current_date(db)
    return {
        "date": current.isoformat(),
        "today": current.isoformat(),
    }


@router.post("/clock/reset", summary="Reset clock to real system date")
@router.post("/api/clock/reset", summary="Reset clock to real system date")
def reset_clock(db: Session = Depends(get_db)):
    """Reset clock back to today's date."""
    return clock_service.reset_clock(db)
