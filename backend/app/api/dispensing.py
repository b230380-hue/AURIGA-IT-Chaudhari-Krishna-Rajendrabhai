"""Dispensing API routes — preview and execute FEFO dispensing."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.allocation import InsufficientStockError
from app.models.dispense import DispenseTransaction, DispenseAllocation
from app.models.medicine import Medicine
from app.schemas.dispense import (
    AllocationDetail,
    DispenseHistoryResponse,
    DispensePreviewResponse,
    DispenseRequest,
    DispenseResponse,
    DispenseTransactionResponse,
)
from app.services import fefo_service

router = APIRouter(prefix="/api", tags=["Dispensing"])


@router.post(
    "/medicines/{medicine_id}/dispense/preview",
    response_model=DispensePreviewResponse,
    summary="Preview FEFO allocation (read-only)",
)
def preview_dispense(
    medicine_id: int,
    data: DispenseRequest,
    db: Session = Depends(get_db),
):
    """
    Preview how units would be allocated across batches using FEFO.
    This is read-only and does NOT modify inventory.
    Includes 'Why this batch?' explainability for the first batch.
    """
    try:
        return fefo_service.preview_dispense(db, medicine_id, data.quantity)
    except ValueError as e:
        msg = str(e)
        if "MEDICINE_NOT_FOUND" in msg:
            raise HTTPException(status_code=404, detail={
                "error": "MEDICINE_NOT_FOUND",
                "message": f"Medicine {medicine_id} not found.",
            })
        if "INVALID_QUANTITY" in msg:
            raise HTTPException(status_code=400, detail={
                "error": "INVALID_QUANTITY",
                "message": msg,
            })
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": msg})


@router.post(
    "/medicines/{medicine_id}/dispense",
    response_model=DispenseResponse,
    summary="Execute FEFO dispensing",
)
def execute_dispense(
    medicine_id: int,
    data: DispenseRequest,
    db: Session = Depends(get_db),
):
    """
    Dispense medicine using FEFO (First Expiry, First Out).

    The operation is transactional:
    - If sellable stock < requested quantity, the entire operation is rejected
      and NO inventory is modified.
    - On success, batch quantities are decremented atomically and
      full allocation records are created for traceability.
    """
    try:
        res = fefo_service.dispense(db, medicine_id, data.quantity)
        from app.services.notification_service import check_and_trigger_reorder_alert
        check_and_trigger_reorder_alert(db, medicine_id)
        return res
    except ValueError as e:
        msg = str(e)
        if "MEDICINE_NOT_FOUND" in msg:
            raise HTTPException(status_code=404, detail={
                "error": "MEDICINE_NOT_FOUND",
                "message": f"Medicine {medicine_id} not found.",
            })
        if "INVALID_QUANTITY" in msg:
            raise HTTPException(status_code=400, detail={
                "error": "INVALID_QUANTITY",
                "message": msg,
            })
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": msg})
    except InsufficientStockError as e:
        raise HTTPException(status_code=409, detail={
            "error": "INSUFFICIENT_SELLABLE_STOCK",
            "message": str(e),
            "requested": e.requested,
            "available": e.available,
        })


@router.get(
    "/dispenses",
    response_model=DispenseHistoryResponse,
    summary="List dispense transactions",
)
def list_dispenses(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve paginated dispense history with allocation details."""
    total = db.query(DispenseTransaction).count()

    txns = (
        db.query(DispenseTransaction)
        .order_by(DispenseTransaction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    transactions = []
    for txn in txns:
        medicine = db.query(Medicine).filter(Medicine.id == txn.medicine_id).first()
        allocations = (
            db.query(DispenseAllocation)
            .filter(DispenseAllocation.dispense_transaction_id == txn.id)
            .all()
        )

        alloc_details = []
        for alloc in allocations:
            from app.models.batch import Batch
            batch = db.query(Batch).filter(Batch.id == alloc.batch_id).first()
            alloc_details.append(
                AllocationDetail(
                    batch_id=alloc.batch_id,
                    batch_number=batch.batch_number if batch else "Unknown",
                    expiry_date=alloc.batch_expiry_date_snapshot,
                    quantity_dispensed=alloc.quantity_dispensed,
                )
            )

        transactions.append(
            DispenseTransactionResponse(
                id=txn.id,
                medicine_id=txn.medicine_id,
                medicine_name=medicine.name if medicine else "Unknown",
                requested_quantity=txn.requested_quantity,
                dispensed_quantity=txn.dispensed_quantity,
                status=txn.status,
                created_at=txn.created_at,
                allocations=alloc_details,
            )
        )

    return DispenseHistoryResponse(transactions=transactions, total=total)


@router.get(
    "/dispenses/{transaction_id}",
    response_model=DispenseTransactionResponse,
    summary="Get dispense transaction details",
)
def get_dispense(transaction_id: int, db: Session = Depends(get_db)):
    """Retrieve a single dispense transaction with allocation details."""
    txn = db.query(DispenseTransaction).filter(DispenseTransaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail={
            "error": "TRANSACTION_NOT_FOUND",
            "message": f"Dispense transaction {transaction_id} not found.",
        })

    medicine = db.query(Medicine).filter(Medicine.id == txn.medicine_id).first()
    allocations = (
        db.query(DispenseAllocation)
        .filter(DispenseAllocation.dispense_transaction_id == txn.id)
        .all()
    )

    alloc_details = []
    for alloc in allocations:
        from app.models.batch import Batch
        batch = db.query(Batch).filter(Batch.id == alloc.batch_id).first()
        alloc_details.append(
            AllocationDetail(
                batch_id=alloc.batch_id,
                batch_number=batch.batch_number if batch else "Unknown",
                expiry_date=alloc.batch_expiry_date_snapshot,
                quantity_dispensed=alloc.quantity_dispensed,
            )
        )

    return DispenseTransactionResponse(
        id=txn.id,
        medicine_id=txn.medicine_id,
        medicine_name=medicine.name if medicine else "Unknown",
        requested_quantity=txn.requested_quantity,
        dispensed_quantity=txn.dispensed_quantity,
        status=txn.status,
        created_at=txn.created_at,
        allocations=alloc_details,
    )
