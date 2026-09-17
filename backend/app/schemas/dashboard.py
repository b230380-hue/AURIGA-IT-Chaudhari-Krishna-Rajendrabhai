"""Pydantic schemas for dashboard and alert views."""

from datetime import date
from pydantic import BaseModel, Field


class ExpiryAlertItem(BaseModel):
    """Single batch in the expiry alert list."""

    batch_id: int
    medicine_id: int
    medicine_name: str
    batch_number: str
    quantity: int
    expiry_date: date
    days_remaining: int
    status: str  # EXPIRED, CRITICAL, EXPIRING_SOON, HEALTHY
    potential_value_at_risk: float | None = None


class ExpiryAlertResponse(BaseModel):
    """Expiry alert results."""

    threshold_days: int
    alerts: list[ExpiryAlertItem]
    summary: dict[str, int] = Field(
        default_factory=dict,
        description="Count by status: EXPIRED, CRITICAL, EXPIRING_SOON",
    )


class DashboardSummary(BaseModel):
    """Top-level dashboard summary cards."""

    total_medicines: int
    total_batches: int
    sellable_units: int
    expired_units: int
    expiring_soon_units: int  # within 30 days
    medicines_in_stock: int
    batches_requiring_attention: int  # expired + critical + expiring_soon


class FefoQueueItem(BaseModel):
    """One batch in the FEFO queue."""

    batch_id: int
    medicine_id: int
    medicine_name: str
    batch_number: str
    quantity: int
    expiry_date: date
    days_until_expiry: int
    status: str
    fefo_priority: int


class InventoryHealthScore(BaseModel):
    """Deterministic inventory health indicator."""

    score: float = Field(description="0-100 health score")
    grade: str = Field(description="A, B, C, D, F")
    sellable_units: int
    expired_units: int
    expiring_soon_units: int
    total_physical_units: int
    sellable_percentage: float
    expired_percentage: float
    explanation: str


class ExpiryExposure(BaseModel):
    """Stock at risk of expiry."""

    units_expiring_within_30_days: int
    units_expiring_within_7_days: int
    potential_value_at_risk_30d: float | None = None
    potential_value_at_risk_7d: float | None = None


class RecentDispense(BaseModel):
    """Recent dispense for dashboard."""

    transaction_id: int
    medicine_name: str
    quantity: int
    batch_count: int
    created_at: str
    status: str


class DashboardResponse(BaseModel):
    """Complete dashboard data."""

    summary: DashboardSummary
    health: InventoryHealthScore
    exposure: ExpiryExposure
    needs_attention: list[ExpiryAlertItem]
    fefo_queue: list[FefoQueueItem]
    recent_dispenses: list[RecentDispense]
