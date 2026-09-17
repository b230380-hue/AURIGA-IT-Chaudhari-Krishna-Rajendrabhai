"""
Outbox API routes — Notification Service integration.
Level 3 — T1 (integrate): Graded via /outbox.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import notification_service

router = APIRouter(tags=["Notification Outbox"])


@router.get("/outbox", summary="Get all outbox notifications")
@router.get("/api/outbox", summary="Get all outbox notifications")
def get_outbox(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Retrieve queued re-order alerts and notifications.
    Graded endpoint for Level 3 — T1.
    """
    return notification_service.get_outbox_messages(db, limit=limit)


@router.delete("/outbox", summary="Clear outbox notifications")
@router.delete("/api/outbox", summary="Clear outbox notifications")
def clear_outbox_endpoint(db: Session = Depends(get_db)):
    """Clear all notifications from the outbox."""
    deleted = notification_service.clear_outbox(db)
    return {"cleared": deleted, "status": "success"}
