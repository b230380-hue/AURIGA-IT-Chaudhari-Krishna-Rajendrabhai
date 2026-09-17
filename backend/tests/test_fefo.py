"""
Tests for the FEFO allocation algorithm (pure domain logic).

Covers:
  - Normal multi-batch FEFO ordering
  - Expired batch exclusion
  - Zero-quantity batch exclusion
  - Insufficient stock (infeasible plan)
  - Single batch allocation
  - 3+ batch allocation
  - Same-expiry tie-breaking
  - Exact available stock
  - Large request
"""

from datetime import date, timedelta
import pytest

from app.domain.allocation import (
    AllocationPlan,
    BatchSnapshot,
    plan_fefo_allocation,
)


@pytest.fixture
def today():
    return date(2026, 9, 17)


def _make_batch(id, number, qty, expiry, received=None):
    return BatchSnapshot(
        id=id,
        batch_number=number,
        quantity=qty,
        expiry_date=expiry,
        received_date=received,
    )


class TestFefoAllocation:
    """Core FEFO allocation tests."""

    def test_normal_fefo_ordering(self, today):
        """B1 (Oct 1, 20) -> B2 (Nov 1, 50) -> B3 (Dec 1, 100). Request 60."""
        batches = [
            _make_batch(1, "B1", 20, date(2026, 10, 1)),
            _make_batch(2, "B2", 50, date(2026, 11, 1)),
            _make_batch(3, "B3", 100, date(2026, 12, 1)),
        ]
        plan = plan_fefo_allocation(batches, 60, today)

        assert plan.feasible is True
        assert plan.total_allocated == 60
        assert len(plan.allocations) == 2

        assert plan.allocations[0].batch_number == "B1"
        assert plan.allocations[0].quantity_to_dispense == 20

        assert plan.allocations[1].batch_number == "B2"
        assert plan.allocations[1].quantity_to_dispense == 40

    def test_expired_batch_excluded(self, today):
        """Expired batch B1 must never participate in allocation."""
        batches = [
            _make_batch(1, "B1-EXP", 100, today - timedelta(days=1)),  # expired
            _make_batch(2, "B2", 30, today + timedelta(days=30)),
        ]
        plan = plan_fefo_allocation(batches, 20, today)

        assert plan.feasible is True
        assert plan.total_allocated == 20
        assert len(plan.allocations) == 1
        assert plan.allocations[0].batch_number == "B2"
        assert plan.allocations[0].quantity_to_dispense == 20

    def test_zero_quantity_batch_excluded(self, today):
        """Zero-stock batch must never participate."""
        batches = [
            _make_batch(1, "B-EMPTY", 0, today + timedelta(days=30)),
            _make_batch(2, "B-FULL", 50, today + timedelta(days=60)),
        ]
        plan = plan_fefo_allocation(batches, 10, today)

        assert plan.feasible is True
        assert len(plan.allocations) == 1
        assert plan.allocations[0].batch_number == "B-FULL"

    def test_insufficient_stock_infeasible(self, today):
        """If sellable < requested, plan is infeasible with zero allocations."""
        batches = [
            _make_batch(1, "B1", 30, today + timedelta(days=30)),
            _make_batch(2, "B2", 20, today + timedelta(days=60)),
        ]
        plan = plan_fefo_allocation(batches, 80, today)

        assert plan.feasible is False
        assert plan.total_allocated == 0
        assert len(plan.allocations) == 0
        assert plan.available_before == 50

    def test_single_batch(self, today):
        """Request fulfilled from one batch."""
        batches = [_make_batch(1, "SOLO", 100, today + timedelta(days=90))]
        plan = plan_fefo_allocation(batches, 25, today)

        assert plan.feasible is True
        assert len(plan.allocations) == 1
        assert plan.allocations[0].quantity_to_dispense == 25
        assert plan.allocations[0].batch_remaining_after == 75

    def test_multi_batch_three_plus(self, today):
        """Request spans 3+ batches."""
        batches = [
            _make_batch(1, "B1", 10, today + timedelta(days=10)),
            _make_batch(2, "B2", 15, today + timedelta(days=20)),
            _make_batch(3, "B3", 20, today + timedelta(days=30)),
            _make_batch(4, "B4", 100, today + timedelta(days=90)),
        ]
        plan = plan_fefo_allocation(batches, 40, today)

        assert plan.feasible is True
        assert plan.total_allocated == 40
        assert len(plan.allocations) == 3
        assert plan.allocations[0].quantity_to_dispense == 10  # B1
        assert plan.allocations[1].quantity_to_dispense == 15  # B2
        assert plan.allocations[2].quantity_to_dispense == 15  # B3 (remaining)

    def test_same_expiry_tie_breaking(self, today):
        """Two batches with same expiry: deterministic ordering by received_date, then id."""
        same_expiry = today + timedelta(days=30)
        batches = [
            _make_batch(2, "B-LATER", 50, same_expiry, today - timedelta(days=5)),
            _make_batch(1, "B-EARLIER", 50, same_expiry, today - timedelta(days=10)),
        ]
        plan = plan_fefo_allocation(batches, 60, today)

        assert plan.feasible is True
        # B-EARLIER should come first (earlier received_date)
        assert plan.allocations[0].batch_number == "B-EARLIER"
        assert plan.allocations[0].quantity_to_dispense == 50
        assert plan.allocations[1].batch_number == "B-LATER"
        assert plan.allocations[1].quantity_to_dispense == 10

    def test_exact_available_stock(self, today):
        """Request exactly equals available stock."""
        batches = [
            _make_batch(1, "B1", 30, today + timedelta(days=10)),
            _make_batch(2, "B2", 20, today + timedelta(days=20)),
        ]
        plan = plan_fefo_allocation(batches, 50, today)

        assert plan.feasible is True
        assert plan.total_allocated == 50
        assert plan.remaining_sellable == 0

    def test_expires_today_is_eligible(self, today):
        """Batch expiring today should be eligible (valid through expiry date)."""
        batches = [_make_batch(1, "TODAY", 30, today)]
        plan = plan_fefo_allocation(batches, 10, today)

        assert plan.feasible is True
        assert plan.allocations[0].batch_number == "TODAY"

    def test_all_expired_no_allocation(self, today):
        """If all batches are expired, plan is infeasible."""
        batches = [
            _make_batch(1, "EXP1", 100, today - timedelta(days=10)),
            _make_batch(2, "EXP2", 200, today - timedelta(days=1)),
        ]
        plan = plan_fefo_allocation(batches, 10, today)

        assert plan.feasible is False
        assert plan.available_before == 0

    def test_remaining_sellable_calculated_correctly(self, today):
        """After allocation, remaining sellable = available - allocated."""
        batches = [
            _make_batch(1, "B1", 30, today + timedelta(days=10)),
            _make_batch(2, "B2", 70, today + timedelta(days=20)),
        ]
        plan = plan_fefo_allocation(batches, 40, today)

        assert plan.feasible is True
        assert plan.available_before == 100
        assert plan.total_allocated == 40
        assert plan.remaining_sellable == 60

    def test_batch_remaining_after_per_allocation(self, today):
        """Each allocation item tracks what would remain in that batch."""
        batches = [_make_batch(1, "B1", 50, today + timedelta(days=10))]
        plan = plan_fefo_allocation(batches, 30, today)

        assert plan.allocations[0].batch_remaining_after == 20

    def test_empty_batches_list(self, today):
        """No batches at all = infeasible."""
        plan = plan_fefo_allocation([], 10, today)
        assert plan.feasible is False
        assert plan.available_before == 0
