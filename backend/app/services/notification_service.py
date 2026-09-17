"""
Notification Service — manages outbox messages and re-order alerts.
Level 3 — T1 (integrate).
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.medicine import Medicine
from app.models.outbox import OutboxMessage
from app.services.inventory_service import get_medicine_stock


def check_and_trigger_reorder_alert(
    db: Session,
    medicine_id: int,
    today=None,
) -> OutboxMessage | None:
    """
    Check if a medicine's in-date (sellable) stock has dropped below its
    reorder_threshold. If so, create and queue an OutboxMessage.
    """
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        return None

    stock = get_medicine_stock(db, medicine_id, today)
    if not stock:
        return None

    threshold = getattr(medicine, "reorder_threshold", 20)
    current_sellable = stock.sellable_stock

    if current_sellable < threshold:
        # Check if an alert for this medicine was already sent today or is pending
        existing = (
            db.query(OutboxMessage)
            .filter(
                OutboxMessage.medicine_id == medicine_id,
                OutboxMessage.current_stock == current_sellable,
            )
            .first()
        )
        if existing:
            return existing

        message_text = (
            f"REORDER ALERT: In-date stock for {medicine.name} has dropped to "
            f"{current_sellable} units (below threshold of {threshold}). "
            f"Please place an order immediately."
        )

        alert = OutboxMessage(
            medicine_id=medicine.id,
            medicine_name=medicine.name,
            event="REORDER_ALERT",
            message=message_text,
            current_stock=current_sellable,
            threshold=threshold,
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    return None


def check_all_medicines_for_reorder(db: Session, today=None) -> list[OutboxMessage]:
    """Check every medicine in inventory for re-order condition."""
    medicines = db.query(Medicine).all()
    created_alerts = []
    for med in medicines:
        alert = check_and_trigger_reorder_alert(db, med.id, today)
        if alert and alert not in created_alerts:
            created_alerts.append(alert)
    return created_alerts


def get_outbox_messages(db: Session, limit: int = 100) -> list[dict]:
    """Retrieve all messages currently in the notification outbox."""
    messages = (
        db.query(OutboxMessage)
        .order_by(OutboxMessage.id.desc())
        .limit(limit)
        .all()
    )
    return [m.to_dict() for m in messages]


def clear_outbox(db: Session) -> int:
    """Clear all messages from the outbox."""
    count = db.query(OutboxMessage).delete()
    db.commit()
    return count
