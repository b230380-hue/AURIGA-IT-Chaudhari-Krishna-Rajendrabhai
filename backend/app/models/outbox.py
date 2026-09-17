"""Outbox Message model for low-stock and reorder notifications."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class OutboxMessage(Base):
    """Represents a notification in the outbox queue."""

    __tablename__ = "outbox_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False)
    medicine_name = Column(String(255), nullable=False)
    event = Column(String(100), nullable=False, default="REORDER_ALERT")
    message = Column(Text, nullable=False)
    current_stock = Column(Integer, nullable=False)
    threshold = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "medicine_id": self.medicine_id,
            "medicine_name": self.medicine_name,
            "event": self.event,
            "message": self.message,
            "current_stock": self.current_stock,
            "threshold": self.threshold,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
