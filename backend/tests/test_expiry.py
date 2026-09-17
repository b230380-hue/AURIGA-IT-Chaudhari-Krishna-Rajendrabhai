"""
Tests for expiry date semantics.

Verifies the centralized date classification logic:
  - expired: expiry_date < today
  - sellable: expiry_date >= today AND quantity > 0
  - batch status classification boundaries
"""

from datetime import date, timedelta
import pytest

from app.domain.expiry import (
    BatchStatus,
    classify_batch,
    days_until_expiry,
    is_expired,
    is_sellable,
)


class TestIsExpired:
    """Tests for the is_expired function."""

    def test_expired_yesterday(self):
        today = date(2026, 9, 17)
        assert is_expired(date(2026, 9, 16), today) is True

    def test_expired_long_ago(self):
        today = date(2026, 9, 17)
        assert is_expired(date(2025, 1, 1), today) is True

    def test_expires_today_is_NOT_expired(self):
        """A batch expiring today is still valid (pharmacy rule)."""
        today = date(2026, 9, 17)
        assert is_expired(date(2026, 9, 17), today) is False

    def test_expires_tomorrow(self):
        today = date(2026, 9, 17)
        assert is_expired(date(2026, 9, 18), today) is False

    def test_expires_far_future(self):
        today = date(2026, 9, 17)
        assert is_expired(date(2028, 12, 31), today) is False


class TestIsSellable:
    """Tests for the is_sellable function."""

    def test_valid_with_stock(self):
        today = date(2026, 9, 17)
        assert is_sellable(date(2026, 10, 1), 50, today) is True

    def test_valid_with_zero_stock(self):
        """Zero quantity is not sellable even if not expired."""
        today = date(2026, 9, 17)
        assert is_sellable(date(2026, 10, 1), 0, today) is False

    def test_expired_with_stock(self):
        """Expired batch is not sellable even with stock."""
        today = date(2026, 9, 17)
        assert is_sellable(date(2026, 9, 16), 100, today) is False

    def test_expires_today_with_stock(self):
        """Batch expiring today remains sellable."""
        today = date(2026, 9, 17)
        assert is_sellable(date(2026, 9, 17), 10, today) is True


class TestDaysUntilExpiry:
    """Tests for days_until_expiry."""

    def test_expires_today(self):
        today = date(2026, 9, 17)
        assert days_until_expiry(date(2026, 9, 17), today) == 0

    def test_expires_tomorrow(self):
        today = date(2026, 9, 17)
        assert days_until_expiry(date(2026, 9, 18), today) == 1

    def test_expired_yesterday(self):
        today = date(2026, 9, 17)
        assert days_until_expiry(date(2026, 9, 16), today) == -1

    def test_far_future(self):
        today = date(2026, 9, 17)
        assert days_until_expiry(date(2027, 9, 17), today) == 365


class TestClassifyBatch:
    """Tests for batch status classification boundaries."""

    def test_expired(self):
        today = date(2026, 9, 17)
        assert classify_batch(date(2026, 9, 16), today) == BatchStatus.EXPIRED

    def test_expires_today_is_critical(self):
        """Expiring today = 0 days remaining = CRITICAL (0 <= 7)."""
        today = date(2026, 9, 17)
        assert classify_batch(date(2026, 9, 17), today) == BatchStatus.CRITICAL

    def test_critical_boundary_7_days(self):
        """Exactly 7 days remaining = CRITICAL."""
        today = date(2026, 9, 17)
        assert classify_batch(today + timedelta(days=7), today) == BatchStatus.CRITICAL

    def test_expiring_soon_boundary_8_days(self):
        """Exactly 8 days remaining = EXPIRING_SOON."""
        today = date(2026, 9, 17)
        assert classify_batch(today + timedelta(days=8), today) == BatchStatus.EXPIRING_SOON

    def test_expiring_soon_boundary_30_days(self):
        """Exactly 30 days remaining = EXPIRING_SOON."""
        today = date(2026, 9, 17)
        assert classify_batch(today + timedelta(days=30), today) == BatchStatus.EXPIRING_SOON

    def test_healthy_boundary_31_days(self):
        """Exactly 31 days remaining = HEALTHY."""
        today = date(2026, 9, 17)
        assert classify_batch(today + timedelta(days=31), today) == BatchStatus.HEALTHY

    def test_healthy_far_future(self):
        today = date(2026, 9, 17)
        assert classify_batch(today + timedelta(days=365), today) == BatchStatus.HEALTHY

    def test_categories_are_mutually_exclusive(self):
        """No date should match two categories."""
        today = date(2026, 9, 17)
        for delta in range(-10, 400):
            d = today + timedelta(days=delta)
            status = classify_batch(d, today)
            assert status in (
                BatchStatus.EXPIRED,
                BatchStatus.CRITICAL,
                BatchStatus.EXPIRING_SOON,
                BatchStatus.HEALTHY,
            )

    def test_expired_never_appears_as_expiring_soon(self):
        """Expired batches must never be classified as expiring soon."""
        today = date(2026, 9, 17)
        for delta in range(-100, 0):
            d = today + timedelta(days=delta)
            assert classify_batch(d, today) == BatchStatus.EXPIRED
