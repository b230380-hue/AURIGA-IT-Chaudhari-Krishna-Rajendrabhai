"""
Centralized expiry-date semantics for PharmaFlow.

RULE (pharmacy-friendly interpretation):
  A batch remains valid THROUGH its printed expiry date.
  It becomes expired AFTER that date.

  expired:       expiry_date < today
  sellable:      expiry_date >= today  AND  quantity > 0
  expiring_soon: expiry_date >= today  AND  days_remaining <= threshold

All comparisons use date-only (no timestamps).
"today" is injectable for deterministic testing.
"""

from datetime import date, timedelta
from enum import Enum


class BatchStatus(str, Enum):
    """Classification of a batch based on its expiry proximity."""

    EXPIRED = "EXPIRED"
    CRITICAL = "CRITICAL"       # 0-7 days remaining
    EXPIRING_SOON = "EXPIRING_SOON"  # 8-30 days remaining
    HEALTHY = "HEALTHY"         # >30 days remaining


def get_today() -> date:
    """Return the current date. Override in tests for determinism."""
    return date.today()


def is_expired(expiry_date: date, today: date | None = None) -> bool:
    """A batch is expired if its expiry_date is strictly before today."""
    today = today or get_today()
    return expiry_date < today


def is_sellable(expiry_date: date, quantity: int, today: date | None = None) -> bool:
    """A batch is sellable if it is not expired and has stock."""
    today = today or get_today()
    return not is_expired(expiry_date, today) and quantity > 0


def days_until_expiry(expiry_date: date, today: date | None = None) -> int:
    """
    Days remaining until expiry.
    Positive = days left (including today).
    Negative = days past expiry.
    Zero = expires today (still valid).
    """
    today = today or get_today()
    return (expiry_date - today).days


def classify_batch(
    expiry_date: date,
    today: date | None = None,
    critical_days: int = 7,
    soon_days: int = 30,
) -> BatchStatus:
    """
    Classify a batch into an expiry status category.

    Categories (mutually exclusive):
      EXPIRED:       expiry_date < today
      CRITICAL:      0 <= days_remaining <= critical_days
      EXPIRING_SOON: critical_days < days_remaining <= soon_days
      HEALTHY:       days_remaining > soon_days
    """
    today = today or get_today()

    if is_expired(expiry_date, today):
        return BatchStatus.EXPIRED

    remaining = days_until_expiry(expiry_date, today)

    if remaining <= critical_days:
        return BatchStatus.CRITICAL
    elif remaining <= soon_days:
        return BatchStatus.EXPIRING_SOON
    else:
        return BatchStatus.HEALTHY
