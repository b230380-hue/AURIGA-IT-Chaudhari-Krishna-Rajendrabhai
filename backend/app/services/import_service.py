"""
Import Service — parses messy batch lists (nulls, unit strings, varying date formats, duplicates).
Level 2 — T4 (messy data).
"""

import csv
from datetime import date, datetime
import io
import re
from typing import Any
from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.models.medicine import Medicine
from app.models.batch import Batch


def _clean_quantity(val: Any) -> int | None:
    """
    Parse messy quantity values such as '10 units', ' 25 boxes ', 50, '100'.
    Returns an integer >= 0, or None if invalid.
    """
    if val is None:
        return None

    if isinstance(val, (int, float)):
        int_val = int(round(val))
        return int_val if int_val >= 0 else None

    s = str(val).strip()
    if not s or s.lower() in ("null", "none", "nan", ""):
        return None

    # Search for numeric digits
    match = re.search(r"\d+", s)
    if match:
        try:
            int_val = int(match.group())
            return int_val if int_val >= 0 else None
        except ValueError:
            return None

    return None


def _clean_date(val: Any) -> date | None:
    """
    Parse varying date formats (dd/mm/yyyy vs yyyy-mm-dd vs dd-mm-yyyy).
    Returns date object or None.
    """
    if val is None:
        return None

    if isinstance(val, date) and not isinstance(val, datetime):
        return val

    if isinstance(val, datetime):
        return val.date()

    s = str(val).strip()
    if not s or s.lower() in ("null", "none", "nan", ""):
        return None

    # Try standard ISO first: YYYY-MM-DD
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass

    # Try common European / UK formats: DD/MM/YYYY, DD-MM-YYYY
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass

    # Fallback to dateutil parser with dayfirst=True
    try:
        dt = date_parser.parse(s, dayfirst=True)
        if 2000 <= dt.year <= 2100:
            return dt.date()
    except Exception:
        pass

    return None


def _extract_field(row: dict[str, Any], candidate_keys: list[str]) -> Any:
    """Case-insensitive key extraction from a dictionary row."""
    lower_map = {k.lower().strip(): v for k, v in row.items()}
    for cand in candidate_keys:
        if cand in lower_map:
            return lower_map[cand]
    return None


def import_batches(db: Session, data: list[dict[str, Any]] | str) -> dict[str, Any]:
    """
    Import a messy batch list and return { imported, deduped, rejected, errors }.

    Handles:
      - Null/missing values (rejected)
      - Strings like '10 units' or '25 boxes' (cleaned to integer)
      - dd/mm/yyyy vs ISO dates (standardized to date)
      - Duplicate rows / existing batches (deduplicated)
    """
    rows: list[dict[str, Any]] = []

    # Parse CSV string if provided
    if isinstance(data, str):
        reader = csv.DictReader(io.StringIO(data.strip()))
        rows = [dict(r) for r in reader]
    elif isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        # Handle wrapping like {"batches": [...]} or {"rows": [...]}
        for key in ("batches", "rows", "data", "items"):
            if key in data and isinstance(data[key], list):
                rows = data[key]
                break
        if not rows and data:
            rows = [data]

    imported_count = 0
    deduped_count = 0
    rejected_count = 0
    errors: list[dict[str, Any]] = []

    seen_in_batch: set[tuple[str, str]] = set()

    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            rejected_count += 1
            errors.append({"row": idx, "reason": "Row is not a valid object/record"})
            continue

        # Extract fields flexibly
        med_name = _extract_field(row, ["medicine_name", "medicine", "name", "drug", "item"])
        batch_num = _extract_field(row, ["batch_number", "batch", "batch_id", "lot_number", "lot", "batch_no"])
        raw_qty = _extract_field(row, ["quantity", "qty", "units", "amount", "count", "stock"])
        raw_expiry = _extract_field(row, ["expiry_date", "expiry", "expiration_date", "exp_date", "expiration"])

        # Validate medicine name
        if not med_name or not str(med_name).strip() or str(med_name).strip().lower() in ("null", "none"):
            rejected_count += 1
            errors.append({"row": idx, "reason": "Missing or null medicine name"})
            continue

        clean_med_name = str(med_name).strip()

        # Validate batch number
        if not batch_num or not str(batch_num).strip() or str(batch_num).strip().lower() in ("null", "none"):
            rejected_count += 1
            errors.append({"row": idx, "reason": "Missing or null batch number"})
            continue

        clean_batch_num = str(batch_num).strip()

        # Clean quantity
        qty = _clean_quantity(raw_qty)
        if qty is None:
            rejected_count += 1
            errors.append({"row": idx, "reason": f"Invalid or unparseable quantity: '{raw_qty}'"})
            continue

        # Clean expiry date
        expiry = _clean_date(raw_expiry)
        if expiry is None:
            rejected_count += 1
            errors.append({"row": idx, "reason": f"Invalid or unparseable expiry date: '{raw_expiry}'"})
            continue

        # Check for deduplication
        dedup_key = (clean_med_name.lower(), clean_batch_num.lower())
        if dedup_key in seen_in_batch:
            deduped_count += 1
            continue

        seen_in_batch.add(dedup_key)

        # Lookup or create medicine
        medicine = (
            db.query(Medicine)
            .filter(Medicine.name.ilike(clean_med_name))
            .first()
        )
        if not medicine:
            medicine = Medicine(name=clean_med_name)
            db.add(medicine)
            db.flush()

        # Check if this batch already exists in DB for this medicine
        existing_batch = (
            db.query(Batch)
            .filter(
                Batch.medicine_id == medicine.id,
                Batch.batch_number == clean_batch_num,
            )
            .first()
        )

        if existing_batch:
            # Batch already in database -> deduplicate (update quantity)
            existing_batch.quantity += qty
            existing_batch.expiry_date = expiry
            deduped_count += 1
        else:
            # New batch -> import
            new_batch = Batch(
                medicine_id=medicine.id,
                batch_number=clean_batch_num,
                quantity=qty,
                initial_quantity=qty,
                expiry_date=expiry,
            )
            db.add(new_batch)
            imported_count += 1

    db.commit()

    return {
        "imported": imported_count,
        "deduped": deduped_count,
        "rejected": rejected_count,
        "total_processed": len(rows),
        "errors": errors,
    }
