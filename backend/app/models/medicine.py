"""Medicine SQLAlchemy model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Medicine(Base):
    """Represents a medicine in the pharmacy inventory."""

    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    generic_name = Column(String(255), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    strength = Column(String(100), nullable=True)
    dosage_form = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True, unique=True)
    reorder_threshold = Column(Integer, nullable=False, default=20)
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
    batches = relationship("Batch", back_populates="medicine", lazy="selectin")
    dispense_transactions = relationship(
        "DispenseTransaction", back_populates="medicine", lazy="select"
    )

    __table_args__ = (
        Index("ix_medicines_name_lower", "name"),
    )

    def __repr__(self):
        return f"<Medicine(id={self.id}, name='{self.name}', strength='{self.strength}')>"
