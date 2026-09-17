"""
Shared test fixtures for PharmaFlow tests.

Uses an in-memory SQLite database for isolation.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.medicine import Medicine
from app.models.batch import Batch
from app.models.dispense import DispenseTransaction, DispenseAllocation


@pytest.fixture
def db_session():
    """Create an in-memory SQLite session for each test."""
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_client():
    """Create test client with isolated database using StaticPool."""
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool
    from app.database import get_db
    from app.main import app
    from app.domain.expiry import reset_simulated_today

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_pragma(conn, _):
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    reset_simulated_today()


@pytest.fixture
def today():
    """Fixed date for deterministic testing."""
    return date(2026, 9, 17)


@pytest.fixture
def sample_medicine(db_session):
    """Create a sample medicine."""
    med = Medicine(
        name="Paracetamol",
        generic_name="Acetaminophen",
        manufacturer="TestCorp",
        strength="500mg",
        dosage_form="Tablet",
        sku="TEST-PARA",
    )
    db_session.add(med)
    db_session.commit()
    db_session.refresh(med)
    return med


@pytest.fixture
def fefo_batches(db_session, sample_medicine, today):
    """
    Create batches for FEFO testing:
      B1: expiry Oct 1, qty 20
      B2: expiry Nov 1, qty 50
      B3: expiry Dec 1, qty 100
    """
    batches = [
        Batch(
            medicine_id=sample_medicine.id,
            batch_number="B1",
            quantity=20,
            initial_quantity=20,
            expiry_date=date(2026, 10, 1),
            received_date=today - timedelta(days=30),
        ),
        Batch(
            medicine_id=sample_medicine.id,
            batch_number="B2",
            quantity=50,
            initial_quantity=50,
            expiry_date=date(2026, 11, 1),
            received_date=today - timedelta(days=20),
        ),
        Batch(
            medicine_id=sample_medicine.id,
            batch_number="B3",
            quantity=100,
            initial_quantity=100,
            expiry_date=date(2026, 12, 1),
            received_date=today - timedelta(days=10),
        ),
    ]
    for b in batches:
        db_session.add(b)
    db_session.commit()
    for b in batches:
        db_session.refresh(b)
    return batches
