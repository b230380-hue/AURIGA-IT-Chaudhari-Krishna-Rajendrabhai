"""
FEFO allocation algorithm — pure domain logic.

FEFO = First Expiry, First Out.

This module provides a single reusable allocation function used by
both the FEFO preview and actual dispensing operations.
The function is pure: it computes allocations without mutating any state.

Ordering: expiry_date ASC, received_date ASC, id ASC
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.expiry import is_expired


@dataclass
class BatchSnapshot:
    """Lightweight batch data for allocation planning."""

    id: int
    batch_number: str
    quantity: int
    expiry_date: date
    received_date: date | None = None
    is_quarantined: bool = False


@dataclass
class AllocationItem:
    """One line of a FEFO allocation plan."""

    batch_id: int
    batch_number: str
    expiry_date: date
    quantity_to_dispense: int
    batch_remaining_after: int


@dataclass
class AllocationPlan:
    """Complete result of FEFO allocation planning."""

    allocations: list[AllocationItem]
    total_allocated: int
    remaining_sellable: int
    feasible: bool
    requested: int
    available_before: int


class InsufficientStockError(Exception):
    """Raised when requested quantity exceeds sellable stock."""

    def __init__(self, requested: int, available: int):
        self.requested = requested
        self.available = available
        super().__init__(
            f"Requested {requested} units but only {available} "
            f"non-expired units are available."
        )


def plan_fefo_allocation(
    batches: list[BatchSnapshot],
    requested_quantity: int,
    today: date | None = None,
) -> AllocationPlan:
    """
    Compute a FEFO allocation plan WITHOUT mutating any data.

    Steps:
      1. Filter out expired and zero-quantity batches.
      2. Sort by expiry_date ASC, received_date ASC, id ASC.
      3. Check total sellable >= requested (if not, return infeasible).
      4. Allocate sequentially from earliest-expiring batches.

    Args:
        batches: List of batch snapshots to consider.
        requested_quantity: Number of units to allocate.
        today: Reference date for expiry checks (injectable).

    Returns:
        AllocationPlan with feasibility and allocation details.
    """
    from app.domain.expiry import get_today

    today = today or get_today()

    # Step 1: Filter eligible batches (not expired, not quarantined, quantity > 0)
    eligible = [
        b
        for b in batches
        if not is_expired(b.expiry_date, today)
        and not getattr(b, "is_quarantined", False)
        and b.quantity > 0
    ]

    # Step 2: Sort FEFO — expiry ASC, received ASC (None last), id ASC
    def sort_key(b: BatchSnapshot):
        return (
            b.expiry_date,
            b.received_date or date.max,
            b.id,
        )

    eligible.sort(key=sort_key)

    # Step 3: Check availability
    available = sum(b.quantity for b in eligible)

    if available < requested_quantity:
        return AllocationPlan(
            allocations=[],
            total_allocated=0,
            remaining_sellable=available,
            feasible=False,
            requested=requested_quantity,
            available_before=available,
        )

    # Step 4: Allocate sequentially
    remaining = requested_quantity
    allocations: list[AllocationItem] = []

    for batch in eligible:
        if remaining <= 0:
            break

        take = min(batch.quantity, remaining)
        allocations.append(
            AllocationItem(
                batch_id=batch.id,
                batch_number=batch.batch_number,
                expiry_date=batch.expiry_date,
                quantity_to_dispense=take,
                batch_remaining_after=batch.quantity - take,
            )
        )
        remaining -= take

    total_allocated = requested_quantity - remaining

    return AllocationPlan(
        allocations=allocations,
        total_allocated=total_allocated,
        remaining_sellable=available - total_allocated,
        feasible=True,
        requested=requested_quantity,
        available_before=available,
    )
