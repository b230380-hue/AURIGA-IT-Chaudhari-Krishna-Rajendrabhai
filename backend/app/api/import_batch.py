"""
Batch Import API routes — messy batch data ingestion.
Level 2 — T4 (messy data).
"""

from typing import Any, Union
from fastapi import APIRouter, Depends, Body, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import import_service

router = APIRouter(tags=["Batch Import"])


@router.post("/batches/import", summary="Import messy batch list")
@router.post("/api/batches/import", summary="Import messy batch list")
@router.post("/import", summary="Import messy batch list (alias)")
@router.post("/api/import", summary="Import messy batch list (alias)")
async def import_batches_endpoint(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Import messy batch list with automatic cleaning, deduplication, and error reporting.
    Returns:
      {
        "imported": <count>,
        "deduped": <count>,
        "rejected": <count>,
        "errors": [...]
      }
    """
    content_type = request.headers.get("content-type", "")

    if "text/csv" in content_type or "text/plain" in content_type:
        body_text = (await request.body()).decode("utf-8")
        return import_service.import_batches(db, body_text)
    else:
        try:
            json_data = await request.json()
            return import_service.import_batches(db, json_data)
        except Exception:
            # Fallback to plain text
            body_text = (await request.body()).decode("utf-8")
            return import_service.import_batches(db, body_text)
