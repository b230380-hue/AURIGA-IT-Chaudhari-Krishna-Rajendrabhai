"""Medicine and batch API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.medicine import (
    MedicineCreate,
    MedicineResponse,
    MedicineSearchResult,
    MedicineStockResponse,
    MedicineUpdate,
)
from app.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.services import inventory_service

router = APIRouter(prefix="/api", tags=["Medicines & Batches"])


# ── Medicine endpoints ─────────────────────────────────────────


@router.get(
    "/medicines",
    response_model=list[MedicineResponse],
    summary="List all medicines",
)
def list_medicines(db: Session = Depends(get_db)):
    """Retrieve all medicines in the pharmacy inventory."""
    return inventory_service.get_all_medicines(db)


@router.post(
    "/medicines",
    response_model=MedicineResponse,
    status_code=201,
    summary="Create a new medicine",
)
def create_medicine(data: MedicineCreate, db: Session = Depends(get_db)):
    """Add a new medicine to the pharmacy inventory."""
    try:
        return inventory_service.create_medicine(db, data)
    except ValueError as e:
        msg = str(e)
        if "DUPLICATE_SKU" in msg:
            raise HTTPException(status_code=409, detail={
                "error": "DUPLICATE_SKU",
                "message": msg,
            })
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": msg})


@router.get(
    "/medicines/search",
    response_model=list[MedicineSearchResult],
    summary="Search medicines with availability",
)
def search_medicines(
    q: str = Query(..., min_length=1, description="Search query"),
    db: Session = Depends(get_db),
):
    """
    Case-insensitive search by medicine name or generic name.
    Returns availability information alongside each result.
    """
    return inventory_service.get_medicine_search_results(db, q)


@router.get(
    "/medicines/{medicine_id}",
    response_model=MedicineResponse,
    summary="Get medicine details",
)
def get_medicine(medicine_id: int, db: Session = Depends(get_db)):
    """Retrieve a single medicine by ID."""
    medicine = inventory_service.get_medicine(db, medicine_id)
    if not medicine:
        raise HTTPException(
            status_code=404,
            detail={"error": "MEDICINE_NOT_FOUND", "message": f"Medicine {medicine_id} not found."},
        )
    return medicine


@router.put(
    "/medicines/{medicine_id}",
    response_model=MedicineResponse,
    summary="Update medicine details",
)
def update_medicine(
    medicine_id: int, data: MedicineUpdate, db: Session = Depends(get_db)
):
    """Update medicine fields. Does not affect batch data."""
    try:
        medicine = inventory_service.update_medicine(db, medicine_id, data)
        if not medicine:
            raise HTTPException(
                status_code=404,
                detail={"error": "MEDICINE_NOT_FOUND", "message": f"Medicine {medicine_id} not found."},
            )
        return medicine
    except ValueError as e:
        msg = str(e)
        if "DUPLICATE_SKU" in msg:
            raise HTTPException(status_code=409, detail={
                "error": "DUPLICATE_SKU",
                "message": msg,
            })
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": msg})


@router.get(
    "/medicines/{medicine_id}/stock",
    response_model=MedicineStockResponse,
    summary="Get medicine stock summary",
)
def get_medicine_stock(medicine_id: int, db: Session = Depends(get_db)):
    """
    Returns sellable, physical, expired, and expiring-soon stock
    for a medicine. Sellable stock excludes expired batches.
    """
    stock = inventory_service.get_medicine_stock(db, medicine_id)
    if not stock:
        raise HTTPException(
            status_code=404,
            detail={"error": "MEDICINE_NOT_FOUND", "message": f"Medicine {medicine_id} not found."},
        )
    return stock


# ── Batch endpoints ────────────────────────────────────────────


@router.get(
    "/medicines/{medicine_id}/batches",
    response_model=list[BatchResponse],
    summary="List batches for a medicine",
)
def list_batches(medicine_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all batches for a medicine with expiry status,
    days until expiry, and FEFO priority.
    """
    medicine = inventory_service.get_medicine(db, medicine_id)
    if not medicine:
        raise HTTPException(
            status_code=404,
            detail={"error": "MEDICINE_NOT_FOUND", "message": f"Medicine {medicine_id} not found."},
        )
    return inventory_service.get_batches_for_medicine(db, medicine_id)


@router.post(
    "/medicines/{medicine_id}/batches",
    response_model=BatchResponse,
    status_code=201,
    summary="Add a batch to a medicine",
)
def create_batch(
    medicine_id: int, data: BatchCreate, db: Session = Depends(get_db)
):
    """
    Add a new batch with quantity, expiry date, and optional pricing.
    The batch's initial_quantity is set to the provided quantity.
    """
    try:
        batch = inventory_service.create_batch(db, medicine_id, data)
        # Return with computed fields
        batches = inventory_service.get_batches_for_medicine(db, medicine_id)
        for b in batches:
            if b.id == batch.id:
                return b
        return batch
    except ValueError as e:
        msg = str(e)
        if "MEDICINE_NOT_FOUND" in msg:
            raise HTTPException(
                status_code=404,
                detail={"error": "MEDICINE_NOT_FOUND", "message": f"Medicine {medicine_id} not found."},
            )
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_ERROR", "message": msg})


@router.put(
    "/batches/{batch_id}",
    response_model=BatchResponse,
    summary="Update batch metadata",
)
def update_batch(
    batch_id: int, data: BatchUpdate, db: Session = Depends(get_db)
):
    """
    Update batch metadata. Quantity changes are administrative corrections.
    Dispensing changes are tracked separately via the dispense workflow.
    """
    batch = inventory_service.update_batch(db, batch_id, data)
    if not batch:
        raise HTTPException(
            status_code=404,
            detail={"error": "BATCH_NOT_FOUND", "message": f"Batch {batch_id} not found."},
        )
    # Return with computed fields
    from app.domain.expiry import classify_batch, days_until_expiry
    status = classify_batch(batch.expiry_date)
    days_left = days_until_expiry(batch.expiry_date)
    return BatchResponse(
        id=batch.id,
        medicine_id=batch.medicine_id,
        batch_number=batch.batch_number,
        quantity=batch.quantity,
        initial_quantity=batch.initial_quantity,
        expiry_date=batch.expiry_date,
        received_date=batch.received_date,
        purchase_price=batch.purchase_price,
        selling_price=batch.selling_price,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        status=status.value,
        days_until_expiry=days_left,
        fefo_priority=None,
    )
