"""
Dashboard service — aggregates data for the pharmacy dashboard.
"""

from datetime import date

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.domain.expiry import (
    BatchStatus,
    classify_batch,
    days_until_expiry,
    is_expired,
    is_sellable,
    get_today,
)
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.models.dispense import DispenseTransaction, DispenseAllocation
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardSummary,
    ExpiryAlertItem,
    ExpiryExposure,
    FefoQueueItem,
    InventoryHealthScore,
    RecentDispense,
)


def get_dashboard(db: Session, today: date | None = None) -> DashboardResponse:
    """Build the complete dashboard response."""
    today = today or get_today()

    summary = _build_summary(db, today)
    health = _build_health_score(db, today)
    exposure = _build_exposure(db, today)
    needs_attention = _build_needs_attention(db, today)
    fefo_queue = _build_fefo_queue(db, today)
    recent = _build_recent_dispenses(db)

    return DashboardResponse(
        summary=summary,
        health=health,
        exposure=exposure,
        needs_attention=needs_attention,
        fefo_queue=fefo_queue,
        recent_dispenses=recent,
    )


def _build_summary(db: Session, today: date) -> DashboardSummary:
    """Calculate top-level summary cards."""
    total_medicines = db.query(func.count(Medicine.id)).scalar() or 0

    batches = db.query(Batch).all()
    total_batches = len(batches)

    sellable_units = 0
    expired_units = 0
    expiring_soon_units = 0
    medicines_in_stock: set[int] = set()
    batches_attention = 0

    for batch in batches:
        if is_expired(batch.expiry_date, today):
            expired_units += batch.quantity
            if batch.quantity > 0:
                batches_attention += 1
        else:
            if batch.quantity > 0:
                sellable_units += batch.quantity
                medicines_in_stock.add(batch.medicine_id)

                status = classify_batch(batch.expiry_date, today)
                if status in (BatchStatus.CRITICAL, BatchStatus.EXPIRING_SOON):
                    expiring_soon_units += batch.quantity
                    batches_attention += 1

    return DashboardSummary(
        total_medicines=total_medicines,
        total_batches=total_batches,
        sellable_units=sellable_units,
        expired_units=expired_units,
        expiring_soon_units=expiring_soon_units,
        medicines_in_stock=len(medicines_in_stock),
        batches_requiring_attention=batches_attention,
    )


def _build_health_score(db: Session, today: date) -> InventoryHealthScore:
    """
    Deterministic inventory health score.

    Score = (sellable / total_physical) * 100, adjusted for expiry risk.
    This is NOT machine learning — it is a simple transparent metric.
    """
    batches = db.query(Batch).all()

    total_physical = sum(b.quantity for b in batches)
    sellable = sum(
        b.quantity for b in batches if is_sellable(b.expiry_date, b.quantity, today)
    )
    expired = sum(b.quantity for b in batches if is_expired(b.expiry_date, today))
    expiring_soon = sum(
        b.quantity
        for b in batches
        if not is_expired(b.expiry_date, today)
        and b.quantity > 0
        and classify_batch(b.expiry_date, today) in (BatchStatus.CRITICAL, BatchStatus.EXPIRING_SOON)
    )

    if total_physical == 0:
        score = 100.0
        explanation = "No inventory to evaluate."
    else:
        sellable_pct = (sellable / total_physical) * 100
        expired_pct = (expired / total_physical) * 100
        expiring_pct = (expiring_soon / total_physical) * 100

        # Score: start at sellable percentage, penalize for expiring-soon risk
        score = sellable_pct - (expiring_pct * 0.3)
        score = max(0, min(100, score))

        parts = []
        parts.append(f"{sellable_pct:.0f}% of physical stock is sellable.")
        if expired > 0:
            parts.append(f"{expired_pct:.0f}% is expired ({expired} units).")
        if expiring_soon > 0:
            parts.append(f"{expiring_pct:.0f}% is expiring soon ({expiring_soon} units).")
        explanation = " ".join(parts)

    # Grade
    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    sellable_pct_val = (sellable / total_physical * 100) if total_physical > 0 else 100
    expired_pct_val = (expired / total_physical * 100) if total_physical > 0 else 0

    return InventoryHealthScore(
        score=round(score, 1),
        grade=grade,
        sellable_units=sellable,
        expired_units=expired,
        expiring_soon_units=expiring_soon,
        total_physical_units=total_physical,
        sellable_percentage=round(sellable_pct_val, 1),
        expired_percentage=round(expired_pct_val, 1),
        explanation=explanation,
    )


def _build_exposure(db: Session, today: date) -> ExpiryExposure:
    """Stock at risk of expiry."""
    batches = db.query(Batch).filter(Batch.quantity > 0).all()

    units_30d = 0
    units_7d = 0
    value_30d = 0.0
    value_7d = 0.0

    for b in batches:
        if is_expired(b.expiry_date, today):
            continue
        days_left = days_until_expiry(b.expiry_date, today)
        if days_left <= 30:
            units_30d += b.quantity
            if b.purchase_price:
                value_30d += b.quantity * b.purchase_price
        if days_left <= 7:
            units_7d += b.quantity
            if b.purchase_price:
                value_7d += b.quantity * b.purchase_price

    return ExpiryExposure(
        units_expiring_within_30_days=units_30d,
        units_expiring_within_7_days=units_7d,
        potential_value_at_risk_30d=round(value_30d, 2) if value_30d > 0 else None,
        potential_value_at_risk_7d=round(value_7d, 2) if value_7d > 0 else None,
    )


def _build_needs_attention(db: Session, today: date) -> list[ExpiryAlertItem]:
    """Top 10 batches needing attention (expired + critical + expiring soon)."""
    batches = (
        db.query(Batch, Medicine.name)
        .join(Medicine, Batch.medicine_id == Medicine.id)
        .filter(Batch.quantity > 0)
        .order_by(Batch.expiry_date.asc())
        .all()
    )

    items: list[ExpiryAlertItem] = []
    for batch, med_name in batches:
        status = classify_batch(batch.expiry_date, today)
        if status in (BatchStatus.EXPIRED, BatchStatus.CRITICAL, BatchStatus.EXPIRING_SOON):
            days_left = days_until_expiry(batch.expiry_date, today)
            value_at_risk = None
            if batch.purchase_price:
                value_at_risk = round(batch.quantity * batch.purchase_price, 2)

            items.append(
                ExpiryAlertItem(
                    batch_id=batch.id,
                    medicine_id=batch.medicine_id,
                    medicine_name=med_name,
                    batch_number=batch.batch_number,
                    quantity=batch.quantity,
                    expiry_date=batch.expiry_date,
                    days_remaining=days_left,
                    status=status.value,
                    potential_value_at_risk=value_at_risk,
                )
            )

    # Sort by urgency
    status_order = {
        BatchStatus.EXPIRED.value: 0,
        BatchStatus.CRITICAL.value: 1,
        BatchStatus.EXPIRING_SOON.value: 2,
    }
    items.sort(key=lambda a: (status_order.get(a.status, 99), a.days_remaining))

    return items[:10]


def _build_fefo_queue(db: Session, today: date) -> list[FefoQueueItem]:
    """Top 10 batches in the global FEFO queue (across all medicines)."""
    batches = (
        db.query(Batch, Medicine.name)
        .join(Medicine, Batch.medicine_id == Medicine.id)
        .filter(Batch.quantity > 0)
        .order_by(Batch.expiry_date.asc(), Batch.received_date.asc(), Batch.id.asc())
        .all()
    )

    items: list[FefoQueueItem] = []
    priority = 1

    for batch, med_name in batches:
        if is_expired(batch.expiry_date, today):
            continue

        status = classify_batch(batch.expiry_date, today)
        days_left = days_until_expiry(batch.expiry_date, today)

        items.append(
            FefoQueueItem(
                batch_id=batch.id,
                medicine_id=batch.medicine_id,
                medicine_name=med_name,
                batch_number=batch.batch_number,
                quantity=batch.quantity,
                expiry_date=batch.expiry_date,
                days_until_expiry=days_left,
                status=status.value,
                fefo_priority=priority,
            )
        )
        priority += 1

        if priority > 10:
            break

    return items


def _build_recent_dispenses(db: Session) -> list[RecentDispense]:
    """Most recent 10 dispense transactions."""
    txns = (
        db.query(DispenseTransaction, Medicine.name)
        .join(Medicine, DispenseTransaction.medicine_id == Medicine.id)
        .order_by(desc(DispenseTransaction.created_at))
        .limit(10)
        .all()
    )

    items: list[RecentDispense] = []
    for txn, med_name in txns:
        batch_count = (
            db.query(func.count(DispenseAllocation.id))
            .filter(DispenseAllocation.dispense_transaction_id == txn.id)
            .scalar()
            or 0
        )
        items.append(
            RecentDispense(
                transaction_id=txn.id,
                medicine_name=med_name,
                quantity=txn.dispensed_quantity,
                batch_count=batch_count,
                created_at=txn.created_at.isoformat() if txn.created_at else "",
                status=txn.status,
            )
        )

    return items
