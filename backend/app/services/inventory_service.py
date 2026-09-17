"""
Inventory service — stock calculations and medicine/batch management.

Handles sellable stock, physical stock, expired stock computations,
and medicine CRUD operations.
"""

from datetime import date

from sqlalchemy import func
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
from app.schemas.medicine import (
    MedicineCreate,
    MedicineSearchResult,
    MedicineStockResponse,
    MedicineUpdate,
)
from app.schemas.batch import BatchCreate, BatchResponse, BatchUpdate


# ── Medicine CRUD ──────────────────────────────────────────────


def create_medicine(db: Session, data: MedicineCreate) -> Medicine:
    """Create a new medicine."""
    # Check SKU uniqueness
    if data.sku:
        existing = db.query(Medicine).filter(Medicine.sku == data.sku).first()
        if existing:
            raise ValueError(f"DUPLICATE_SKU: SKU '{data.sku}' already exists.")

    medicine = Medicine(**data.model_dump())
    db.add(medicine)
    db.commit()
    db.refresh(medicine)
    return medicine


def get_medicine(db: Session, medicine_id: int) -> Medicine | None:
    """Get a medicine by ID."""
    return db.query(Medicine).filter(Medicine.id == medicine_id).first()


def get_all_medicines(db: Session) -> list[Medicine]:
    """Get all medicines."""
    return db.query(Medicine).order_by(Medicine.name).all()


def update_medicine(db: Session, medicine_id: int, data: MedicineUpdate) -> Medicine | None:
    """Update medicine fields."""
    medicine = get_medicine(db, medicine_id)
    if not medicine:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # Check SKU uniqueness if being changed
    if "sku" in update_data and update_data["sku"]:
        existing = (
            db.query(Medicine)
            .filter(Medicine.sku == update_data["sku"], Medicine.id != medicine_id)
            .first()
        )
        if existing:
            raise ValueError(f"DUPLICATE_SKU: SKU '{update_data['sku']}' already exists.")

    for field, value in update_data.items():
        setattr(medicine, field, value)

    db.commit()
    db.refresh(medicine)
    return medicine


def search_medicines(db: Session, query: str) -> list[Medicine]:
    """Case-insensitive medicine search by name or generic_name."""
    q = f"%{query}%"
    return (
        db.query(Medicine)
        .filter(
            (func.lower(Medicine.name).like(func.lower(q)))
            | (func.lower(Medicine.generic_name).like(func.lower(q)))
        )
        .order_by(Medicine.name)
        .all()
    )


# ── Batch CRUD ─────────────────────────────────────────────────


def create_batch(db: Session, medicine_id: int, data: BatchCreate) -> Batch:
    """Add a new batch to a medicine."""
    medicine = get_medicine(db, medicine_id)
    if not medicine:
        raise ValueError("MEDICINE_NOT_FOUND")

    batch = Batch(
        medicine_id=medicine_id,
        batch_number=data.batch_number,
        quantity=data.quantity,
        initial_quantity=data.quantity,
        expiry_date=data.expiry_date,
        received_date=data.received_date,
        purchase_price=data.purchase_price,
        selling_price=data.selling_price,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def get_batches_for_medicine(
    db: Session, medicine_id: int, today: date | None = None
) -> list[BatchResponse]:
    """Get all batches for a medicine with computed status fields."""
    today = today or get_today()

    batches = (
        db.query(Batch)
        .filter(Batch.medicine_id == medicine_id)
        .order_by(Batch.expiry_date.asc(), Batch.id.asc())
        .all()
    )

    # Calculate FEFO priority (only for sellable batches)
    fefo_priority = 1
    result = []

    for batch in batches:
        status = classify_batch(batch.expiry_date, today)
        days_left = days_until_expiry(batch.expiry_date, today)
        priority = None

        if is_sellable(batch.expiry_date, batch.quantity, today):
            priority = fefo_priority
            fefo_priority += 1

        resp = BatchResponse(
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
            fefo_priority=priority,
            is_quarantined=getattr(batch, "is_quarantined", False),
            is_flagged=getattr(batch, "is_flagged", False),
            quarantine_reason=getattr(batch, "quarantine_reason", None),
        )
        result.append(resp)

    return result


def update_batch(db: Session, batch_id: int, data: BatchUpdate) -> Batch | None:
    """Update batch metadata (administrative correction)."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(batch, field, value)

    db.commit()
    db.refresh(batch)
    return batch


# ── Stock Calculations ─────────────────────────────────────────


def get_medicine_stock(
    db: Session, medicine_id: int, today: date | None = None
) -> MedicineStockResponse | None:
    """Calculate comprehensive stock metrics for a medicine."""
    today = today or get_today()

    medicine = get_medicine(db, medicine_id)
    if not medicine:
        return None

    batches = db.query(Batch).filter(Batch.medicine_id == medicine_id).all()

    physical_stock = 0
    sellable_stock = 0
    expired_stock = 0
    expiring_soon_stock = 0
    total_batches = len(batches)
    valid_batches = 0
    expired_batches = 0
    next_expiry_date = None
    next_expiry_days = None

    for batch in batches:
        physical_stock += batch.quantity
        is_quar = getattr(batch, "is_quarantined", False)

        if is_expired(batch.expiry_date, today) or is_quar:
            expired_stock += batch.quantity
            expired_batches += 1
        else:
            if batch.quantity > 0:
                valid_batches += 1
                sellable_stock += batch.quantity

                # Track nearest valid expiry
                if next_expiry_date is None or batch.expiry_date < next_expiry_date:
                    next_expiry_date = batch.expiry_date

                # Expiring soon (within 30 days)
                status = classify_batch(batch.expiry_date, today)
                if status in (BatchStatus.CRITICAL, BatchStatus.EXPIRING_SOON):
                    expiring_soon_stock += batch.quantity
            else:
                valid_batches += 0  # zero-stock valid batch

    next_expiry_days_val = None
    next_expiry_str = None
    if next_expiry_date:
        next_expiry_days_val = days_until_expiry(next_expiry_date, today)
        next_expiry_str = next_expiry_date.isoformat()

    return MedicineStockResponse(
        medicine_id=medicine.id,
        medicine_name=medicine.name,
        strength=medicine.strength,
        dosage_form=medicine.dosage_form,
        physical_stock=physical_stock,
        sellable_stock=sellable_stock,
        expired_stock=expired_stock,
        expiring_soon_stock=expiring_soon_stock,
        total_batches=total_batches,
        valid_batches=valid_batches,
        expired_batches=expired_batches,
        next_expiry_date=next_expiry_str,
        next_expiry_days=next_expiry_days_val,
    )


def get_medicine_search_results(
    db: Session, query: str, today: date | None = None
) -> list[MedicineSearchResult]:
    """Search medicines with availability info."""
    today = today or get_today()
    medicines = search_medicines(db, query)
    results = []

    for med in medicines:
        stock = get_medicine_stock(db, med.id, today)
        if not stock:
            continue

        if stock.sellable_stock > 20:
            availability = "IN_STOCK"
        elif stock.sellable_stock > 0:
            availability = "LOW_STOCK"
        else:
            availability = "NO_SELLABLE_STOCK"

        results.append(
            MedicineSearchResult(
                id=med.id,
                name=med.name,
                generic_name=med.generic_name,
                strength=med.strength,
                dosage_form=med.dosage_form,
                manufacturer=med.manufacturer,
                sellable_stock=stock.sellable_stock,
                valid_batches=stock.valid_batches,
                expired_batches=stock.expired_batches,
                next_expiry_date=stock.next_expiry_date,
                next_expiry_days=stock.next_expiry_days,
                availability_status=availability,
            )
        )

    return results
