"""Dispense transaction and allocation SQLAlchemy models."""

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base


class DispenseTransaction(Base):
    """Represents a dispensing event — one customer request for medicine."""

    __tablename__ = "dispense_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(
        Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
    )
    requested_quantity = Column(Integer, nullable=False)
    dispensed_quantity = Column(Integer, nullable=False)
    status = Column(
        String(20), nullable=False, default="COMPLETED"
    )  # COMPLETED, FAILED
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    medicine = relationship("Medicine", back_populates="dispense_transactions")
    allocations = relationship(
        "DispenseAllocation",
        back_populates="transaction",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "requested_quantity > 0", name="ck_dispense_requested_positive"
        ),
        CheckConstraint(
            "dispensed_quantity >= 0", name="ck_dispense_dispensed_non_negative"
        ),
    )

    def __repr__(self):
        return (
            f"<DispenseTransaction(id={self.id}, medicine_id={self.medicine_id}, "
            f"requested={self.requested_quantity}, dispensed={self.dispensed_quantity})>"
        )


class DispenseAllocation(Base):
    """Records which batch supplied how many units for a dispense transaction."""

    __tablename__ = "dispense_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dispense_transaction_id = Column(
        Integer,
        ForeignKey("dispense_transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id = Column(
        Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False
    )
    quantity_dispensed = Column(Integer, nullable=False)
    batch_expiry_date_snapshot = Column(Date, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    transaction = relationship("DispenseTransaction", back_populates="allocations")
    batch = relationship("Batch", back_populates="allocations")

    __table_args__ = (
        CheckConstraint(
            "quantity_dispensed > 0", name="ck_allocation_quantity_positive"
        ),
    )

    def __repr__(self):
        return (
            f"<DispenseAllocation(id={self.id}, "
            f"tx={self.dispense_transaction_id}, batch={self.batch_id}, "
            f"qty={self.quantity_dispensed})>"
        )
