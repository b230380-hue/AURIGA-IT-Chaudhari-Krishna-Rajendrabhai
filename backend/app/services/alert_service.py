"""
Alert service — expiry alerts and batch attention tracking.
"""

from datetime import date

from sqlalchemy.orm import Session

from app.domain.expiry import (
    BatchStatus,
    classify_batch,
    days_until_expiry,
    get_today,
)
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.schemas.dashboard import ExpiryAlertItem, ExpiryAlertResponse


def get_expiry_alerts(
    db: Session, threshold_days: int = 30, today: date | None = None
) -> ExpiryAlertResponse:
    """
    Get batches that are expired or expiring within threshold_days.

    Returns alerts sorted by urgency (expired first, then by days remaining).
    """
    today = today or get_today()

    # Query all batches with quantity > 0 (physical stock matters for alerts)
    batches = (
        db.query(Batch, Medicine.name)
        .join(Medicine, Batch.medicine_id == Medicine.id)
        .filter(Batch.quantity > 0)
        .order_by(Batch.expiry_date.asc())
        .all()
    )

    alerts: list[ExpiryAlertItem] = []
    summary: dict[str, int] = {
        "EXPIRED": 0,
        "CRITICAL": 0,
        "EXPIRING_SOON": 0,
    }

    for batch, medicine_name in batches:
        status = classify_batch(batch.expiry_date, today)
        days_left = days_until_expiry(batch.expiry_date, today)

        # Include expired + anything within threshold
        if status == BatchStatus.EXPIRED or (
            status != BatchStatus.EXPIRED and days_left <= threshold_days
        ):
            value_at_risk = None
            if batch.purchase_price is not None:
                value_at_risk = round(batch.quantity * batch.purchase_price, 2)

            alerts.append(
                ExpiryAlertItem(
                    batch_id=batch.id,
                    medicine_id=batch.medicine_id,
                    medicine_name=medicine_name,
                    batch_number=batch.batch_number,
                    quantity=batch.quantity,
                    expiry_date=batch.expiry_date,
                    days_remaining=days_left,
                    status=status.value,
                    potential_value_at_risk=value_at_risk,
                )
            )

            if status.value in summary:
                summary[status.value] += 1

    # Sort: EXPIRED first, then by days remaining ascending
    status_order = {
        BatchStatus.EXPIRED.value: 0,
        BatchStatus.CRITICAL.value: 1,
        BatchStatus.EXPIRING_SOON.value: 2,
        BatchStatus.HEALTHY.value: 3,
    }
    alerts.sort(key=lambda a: (status_order.get(a.status, 99), a.days_remaining))

    return ExpiryAlertResponse(
        threshold_days=threshold_days,
        alerts=alerts,
        summary=summary,
    )
