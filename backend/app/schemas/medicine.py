"""Pydantic schemas for Medicine entities."""

from datetime import datetime
from pydantic import BaseModel, Field


class MedicineCreate(BaseModel):
    """Schema for creating a new medicine."""

    name: str = Field(..., min_length=1, max_length=255, description="Medicine name")
    generic_name: str | None = Field(None, max_length=255)
    manufacturer: str | None = Field(None, max_length=255)
    strength: str | None = Field(None, max_length=100, description="e.g. 500mg")
    dosage_form: str | None = Field(
        None, max_length=100, description="e.g. Tablet, Capsule, Syrup"
    )
    sku: str | None = Field(None, max_length=100, description="Unique stock keeping unit")


class MedicineUpdate(BaseModel):
    """Schema for updating a medicine."""

    name: str | None = Field(None, min_length=1, max_length=255)
    generic_name: str | None = Field(None, max_length=255)
    manufacturer: str | None = Field(None, max_length=255)
    strength: str | None = Field(None, max_length=100)
    dosage_form: str | None = Field(None, max_length=100)
    sku: str | None = Field(None, max_length=100)


class MedicineResponse(BaseModel):
    """Schema for medicine API responses."""

    id: int
    name: str
    generic_name: str | None = None
    manufacturer: str | None = None
    strength: str | None = None
    dosage_form: str | None = None
    sku: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MedicineStockResponse(BaseModel):
    """Stock summary for a medicine."""

    medicine_id: int
    medicine_name: str
    strength: str | None = None
    dosage_form: str | None = None
    physical_stock: int = Field(description="Total stock including expired")
    sellable_stock: int = Field(description="Stock excluding expired batches")
    expired_stock: int = Field(description="Stock in expired batches")
    expiring_soon_stock: int = Field(description="Stock expiring within threshold")
    total_batches: int
    valid_batches: int
    expired_batches: int
    next_expiry_date: str | None = Field(
        None, description="Nearest expiry among valid batches"
    )
    next_expiry_days: int | None = None


class MedicineSearchResult(BaseModel):
    """Search result combining medicine info with stock availability."""

    id: int
    name: str
    generic_name: str | None = None
    strength: str | None = None
    dosage_form: str | None = None
    manufacturer: str | None = None
    sellable_stock: int
    valid_batches: int
    expired_batches: int
    next_expiry_date: str | None = None
    next_expiry_days: int | None = None
    availability_status: str  # IN_STOCK, LOW_STOCK, NO_SELLABLE_STOCK

    model_config = {"from_attributes": True}
