"""Batch SQLAlchemy model."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Batch(Base):
    """Represents a batch of a medicine with its own expiry date and quantity."""

    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(
        Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False
    )
    batch_number = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    initial_quantity = Column(Integer, nullable=False, default=0)
    expiry_date = Column(Date, nullable=False)
    received_date = Column(Date, nullable=True)
    purchase_price = Column(Float, nullable=True)
    selling_price = Column(Float, nullable=True)
    is_quarantined = Column(Boolean, nullable=False, default=False)
    is_flagged = Column(Boolean, nullable=False, default=False)
    quarantine_reason = Column(String(200), nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    medicine = relationship("Medicine", back_populates="batches")
    allocations = relationship("DispenseAllocation", back_populates="batch", lazy="select")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_batch_quantity_non_negative"),
        CheckConstraint(
            "initial_quantity >= 0", name="ck_batch_initial_quantity_non_negative"
        ),
        Index("ix_batches_medicine_expiry", "medicine_id", "expiry_date"),
        Index("ix_batches_expiry_date", "expiry_date"),
    )

    def __repr__(self):
        return (
            f"<Batch(id={self.id}, batch_number='{self.batch_number}', "
            f"qty={self.quantity}, expiry={self.expiry_date})>"
        )
