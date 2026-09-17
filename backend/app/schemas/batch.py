"""Pydantic schemas for Batch entities."""

from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator


class BatchCreate(BaseModel):
    """Schema for adding a new batch."""

    batch_number: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(..., ge=0, description="Initial quantity")
    expiry_date: date = Field(..., description="Batch expiry date")
    received_date: date | None = Field(None, description="Date batch was received")
    purchase_price: float | None = Field(None, ge=0)
    selling_price: float | None = Field(None, ge=0)

    @field_validator("expiry_date")
    @classmethod
    def expiry_must_be_valid_date(cls, v: date) -> date:
        """Expiry date must be a valid date (can be past for record-keeping)."""
        return v


class BatchUpdate(BaseModel):
    """Schema for updating batch metadata."""

    batch_number: str | None = Field(None, min_length=1, max_length=100)
    received_date: date | None = None
    purchase_price: float | None = Field(None, ge=0)
    selling_price: float | None = Field(None, ge=0)
    quantity: int | None = Field(None, ge=0, description="Administrative stock correction")


class BatchResponse(BaseModel):
    """Schema for batch API responses."""

    id: int
    medicine_id: int
    batch_number: str
    quantity: int
    initial_quantity: int
    expiry_date: date
    received_date: date | None = None
    purchase_price: float | None = None
    selling_price: float | None = None
    created_at: datetime
    updated_at: datetime
    # Computed fields (populated by service)
    status: str | None = None
    days_until_expiry: int | None = None
    fefo_priority: int | None = None

    model_config = {"from_attributes": True}
