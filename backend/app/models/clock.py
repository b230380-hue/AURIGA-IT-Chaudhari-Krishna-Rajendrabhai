"""System Clock model for simulated time tracking."""

from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, Integer, Boolean

from app.database import Base


class SystemClock(Base):
    """Stores the current simulated date and metadata for the daily job."""

    __tablename__ = "system_clock"

    id = Column(Integer, primary_key=True, default=1)
    simulated_date = Column(Date, nullable=False, default=date.today)
    is_simulated = Column(Boolean, nullable=False, default=False)
    last_job_run = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
