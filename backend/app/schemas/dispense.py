"""Pydantic schemas for dispensing operations."""

from datetime import date, datetime
from pydantic import BaseModel, Field


class DispenseRequest(BaseModel):
    """Request to dispense medicine."""

    quantity: int = Field(..., gt=0, description="Number of units to dispense")


class AllocationDetail(BaseModel):
    """Detail of one batch allocation within a dispensing operation."""

    batch_id: int
    batch_number: str
    expiry_date: date
    quantity_dispensed: int
    batch_remaining_after: int | None = None


class DispensePreviewResponse(BaseModel):
    """Preview of FEFO allocation without committing."""

    medicine_id: int
    medicine_name: str
    requested_quantity: int
    feasible: bool
    available_stock: int
    allocation_strategy: str = "FEFO"
    allocations: list[AllocationDetail] = []
    remaining_sellable_after: int | None = None
    why_first_batch: str | None = Field(
        None, description="Explainability for the first recommended batch"
    )


class DispenseResponse(BaseModel):
    """Result of a completed dispensing operation."""

    transaction_id: int
    medicine_id: int
    medicine_name: str
    requested_quantity: int
    dispensed_quantity: int
    allocation_strategy: str = "FEFO"
    allocations: list[AllocationDetail]
    remaining_sellable_stock: int
    status: str
    created_at: datetime


class DispenseTransactionResponse(BaseModel):
    """Response for a single dispense transaction."""

    id: int
    medicine_id: int
    medicine_name: str | None = None
    requested_quantity: int
    dispensed_quantity: int
    status: str
    created_at: datetime
    allocations: list[AllocationDetail] = []

    model_config = {"from_attributes": True}


class DispenseHistoryResponse(BaseModel):
    """Paginated dispense history."""

    transactions: list[DispenseTransactionResponse]
    total: int
