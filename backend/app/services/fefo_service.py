"""
FEFO dispensing service — orchestrates preview and actual dispense operations.

Uses the pure domain allocation algorithm for both preview and dispense,
ensuring identical FEFO logic is applied in both cases.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.domain.allocation import (
    AllocationPlan,
    BatchSnapshot,
    InsufficientStockError,
    plan_fefo_allocation,
)
from app.domain.expiry import days_until_expiry, get_today
from app.models.batch import Batch
from app.models.dispense import DispenseAllocation, DispenseTransaction
from app.models.medicine import Medicine
from app.schemas.dispense import (
    AllocationDetail,
    DispensePreviewResponse,
    DispenseResponse,
)

logger = logging.getLogger(__name__)


def _get_batch_snapshots(db: Session, medicine_id: int) -> list[BatchSnapshot]:
    """Load all batches for a medicine as lightweight snapshots."""
    batches = (
        db.query(Batch)
        .filter(Batch.medicine_id == medicine_id)
        .all()
    )
    return [
        BatchSnapshot(
            id=b.id,
            batch_number=b.batch_number,
            quantity=b.quantity,
            expiry_date=b.expiry_date,
            received_date=b.received_date,
            is_quarantined=getattr(b, "is_quarantined", False),
        )
        for b in batches
    ]


def _build_why_first_batch(plan: AllocationPlan, today: date) -> str | None:
    """Generate explainability text for the first recommended batch."""
    if not plan.allocations:
        return None

    first = plan.allocations[0]
    days_left = days_until_expiry(first.expiry_date, today)

    return (
        f"Batch {first.batch_number} is recommended first because it is the "
        f"earliest-expiring non-expired batch with available stock. "
        f"It expires on {first.expiry_date.isoformat()} "
        f"({days_left} day{'s' if days_left != 1 else ''} from now) "
        f"with {first.quantity_to_dispense} unit{'s' if first.quantity_to_dispense != 1 else ''} "
        f"available for this order."
    )


def preview_dispense(
    db: Session, medicine_id: int, quantity: int, today: date | None = None
) -> DispensePreviewResponse:
    """
    Preview FEFO allocation WITHOUT modifying inventory.

    Returns the planned allocation so the pharmacist can review
    before confirming.
    """
    today = today or get_today()

    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise ValueError("MEDICINE_NOT_FOUND")

    if quantity <= 0:
        raise ValueError("INVALID_QUANTITY: Quantity must be greater than zero.")

    snapshots = _get_batch_snapshots(db, medicine_id)
    plan = plan_fefo_allocation(snapshots, quantity, today)

    allocations = [
        AllocationDetail(
            batch_id=a.batch_id,
            batch_number=a.batch_number,
            expiry_date=a.expiry_date,
            quantity_dispensed=a.quantity_to_dispense,
            batch_remaining_after=a.batch_remaining_after,
        )
        for a in plan.allocations
    ]

    why_first = _build_why_first_batch(plan, today) if plan.feasible else None

    return DispensePreviewResponse(
        medicine_id=medicine.id,
        medicine_name=medicine.name,
        requested_quantity=quantity,
        feasible=plan.feasible,
        available_stock=plan.available_before,
        allocations=allocations,
        remaining_sellable_after=plan.remaining_sellable if plan.feasible else None,
        why_first_batch=why_first,
    )


def dispense(
    db: Session, medicine_id: int, quantity: int, today: date | None = None
) -> DispenseResponse:
    """
    Execute a FEFO dispense operation atomically.

    Steps:
      1. Validate medicine exists and quantity is valid.
      2. Load batch snapshots.
      3. Plan allocation (pure, no mutations).
      4. If infeasible, reject WITHOUT any mutations.
      5. If feasible, update batch quantities, create transaction + allocations.
      6. Commit atomically.

    Returns:
        DispenseResponse with full allocation details.

    Raises:
        ValueError: For invalid inputs or business rule violations.
        InsufficientStockError: When sellable stock < requested quantity.
    """
    today = today or get_today()

    # 1. Validate
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise ValueError("MEDICINE_NOT_FOUND")

    if quantity <= 0:
        raise ValueError("INVALID_QUANTITY: Quantity must be greater than zero.")

    # 2. Load snapshots
    snapshots = _get_batch_snapshots(db, medicine_id)

    # 3. Plan (pure function — no side effects)
    plan = plan_fefo_allocation(snapshots, quantity, today)

    # 4. Reject if infeasible — NO mutations at all
    if not plan.feasible:
        logger.warning(
            "Dispense rejected: requested=%d, available=%d, medicine_id=%d",
            quantity,
            plan.available_before,
            medicine_id,
        )
        raise InsufficientStockError(quantity, plan.available_before)

    # 5. Execute atomically
    try:
        # Create transaction record
        transaction = DispenseTransaction(
            medicine_id=medicine_id,
            requested_quantity=quantity,
            dispensed_quantity=plan.total_allocated,
            status="COMPLETED",
        )
        db.add(transaction)
        db.flush()  # Get transaction ID

        # Apply allocations
        for alloc in plan.allocations:
            # Update batch quantity
            batch = db.query(Batch).filter(Batch.id == alloc.batch_id).first()
            if batch is None:
                raise RuntimeError(f"Batch {alloc.batch_id} disappeared during dispense")

            batch.quantity -= alloc.quantity_to_dispense

            if batch.quantity < 0:
                raise RuntimeError(
                    f"Negative quantity on batch {batch.batch_number}: "
                    f"attempted to dispense {alloc.quantity_to_dispense} "
                    f"from {batch.quantity + alloc.quantity_to_dispense}"
                )

            # Create allocation record
            allocation_record = DispenseAllocation(
                dispense_transaction_id=transaction.id,
                batch_id=alloc.batch_id,
                quantity_dispensed=alloc.quantity_to_dispense,
                batch_expiry_date_snapshot=alloc.expiry_date,
            )
            db.add(allocation_record)

        # 6. Commit
        db.commit()
        db.refresh(transaction)

        logger.info(
            "Dispense completed: tx=%d, medicine=%s, qty=%d, batches=%d",
            transaction.id,
            medicine.name,
            plan.total_allocated,
            len(plan.allocations),
        )

        return DispenseResponse(
            transaction_id=transaction.id,
            medicine_id=medicine.id,
            medicine_name=medicine.name,
            requested_quantity=quantity,
            dispensed_quantity=plan.total_allocated,
            allocations=[
                AllocationDetail(
                    batch_id=a.batch_id,
                    batch_number=a.batch_number,
                    expiry_date=a.expiry_date,
                    quantity_dispensed=a.quantity_to_dispense,
                    batch_remaining_after=a.batch_remaining_after,
                )
                for a in plan.allocations
            ],
            remaining_sellable_stock=plan.remaining_sellable,
            status=transaction.status,
            created_at=transaction.created_at,
        )

    except Exception:
        db.rollback()
        logger.exception("Dispense failed, transaction rolled back")
        raise
