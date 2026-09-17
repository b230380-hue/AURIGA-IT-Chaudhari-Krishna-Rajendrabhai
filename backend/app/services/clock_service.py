"""
Clock Service — manages simulated system clock and automated daily jobs.
Level 1 — T2 (automation).
"""

from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.domain.expiry import get_today, set_simulated_today, reset_simulated_today
from app.models.batch import Batch
from app.models.clock import SystemClock
from app.services.notification_service import check_all_medicines_for_reorder


def get_current_date(db: Session) -> date:
    """Get the current active date (simulated date if set, else real system date)."""
    clock = db.query(SystemClock).filter(SystemClock.id == 1).first()
    if clock and clock.is_simulated and clock.simulated_date:
        set_simulated_today(clock.simulated_date)
        return clock.simulated_date
    return date.today()


def run_daily_job(db: Session, current_date: date) -> dict:
    """
    Execute daily automated tasks:
      1. Flags batches expiring within 7 days (today <= expiry <= today + 7d).
      2. Quarantines expired batches (expiry < today).
      3. Checks reorder thresholds and sends outbox notifications.
      4. Reports counts.
    """
    batches = db.query(Batch).all()

    newly_quarantined = 0
    total_quarantined = 0
    flagged_count = 0
    active_batches = 0

    seven_days_out = current_date + timedelta(days=7)

    for b in batches:
        # Expired check
        if b.expiry_date < current_date:
            if not b.is_quarantined:
                b.is_quarantined = True
                b.quarantine_reason = f"EXPIRED: Expired on {b.expiry_date.isoformat()}"
                newly_quarantined += 1
            total_quarantined += 1
            b.is_flagged = False
        else:
            # In-date batch
            if current_date <= b.expiry_date <= seven_days_out and b.quantity > 0:
                b.is_flagged = True
                flagged_count += 1
            else:
                b.is_flagged = False

            if not b.is_quarantined and b.quantity > 0:
                active_batches += 1

    # Check medicines for low stock triggered by newly quarantined batches
    alerts_triggered = check_all_medicines_for_reorder(db, current_date)

    db.commit()

    return {
        "date": current_date.isoformat(),
        "quarantined": newly_quarantined,
        "quarantined_count": newly_quarantined,
        "total_quarantined": total_quarantined,
        "flagged": flagged_count,
        "flagged_count": flagged_count,
        "expiring_within_7_days": flagged_count,
        "active_batches": active_batches,
        "reorder_alerts_triggered": len(alerts_triggered),
        "report": (
            f"Daily job executed for {current_date.isoformat()}: "
            f"{newly_quarantined} newly quarantined, "
            f"{flagged_count} flagged expiring within 7 days, "
            f"{len(alerts_triggered)} re-order alerts triggered."
        ),
    }


def advance_clock(
    db: Session,
    target_date: date | str | None = None,
    days: int | None = None,
) -> dict:
    """
    Advance or set the clock and run the daily job.
    Supports setting to a specific date or advancing by N days (default 1).
    """
    clock = db.query(SystemClock).filter(SystemClock.id == 1).first()
    if not clock:
        clock = SystemClock(id=1, simulated_date=date.today(), is_simulated=True)
        db.add(clock)
        db.flush()

    # Determine next date
    if target_date:
        if isinstance(target_date, str):
            next_date = date.fromisoformat(target_date)
        else:
            next_date = target_date
    elif days is not None:
        base_date = clock.simulated_date if clock.is_simulated else date.today()
        next_date = base_date + timedelta(days=days)
    else:
        base_date = clock.simulated_date if clock.is_simulated else date.today()
        next_date = base_date + timedelta(days=1)

    # Persist in DB and sync memory state
    clock.simulated_date = next_date
    clock.is_simulated = True
    clock.last_job_run = datetime.now(timezone.utc)
    set_simulated_today(next_date)
    db.commit()

    # Run the daily job for the new date
    report = run_daily_job(db, next_date)
    return report


def reset_clock(db: Session) -> dict:
    """Reset simulated clock back to the real system date."""
    clock = db.query(SystemClock).filter(SystemClock.id == 1).first()
    if clock:
        clock.is_simulated = False
        clock.simulated_date = date.today()
        db.commit()

    reset_simulated_today()
    real_today = date.today()
    return run_daily_job(db, real_today)
