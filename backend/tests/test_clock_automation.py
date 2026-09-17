"""
Tests for Level 1 — T2 (automation):
Daily job that flags batches expiring within 7 days and quarantines expired ones;
reports counts. Graded via POST /clock.
"""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.domain.expiry import get_today, reset_simulated_today, set_simulated_today
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.services import clock_service


class TestClockAutomationService:
    """Test the daily automation job service logic."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        self.db = db_session
        reset_simulated_today()

        # Create medicine
        med = Medicine(name="Amoxicillin", strength="500mg")
        db_session.add(med)
        db_session.flush()
        self.med_id = med.id

        base_date = date(2026, 9, 1)

        # Batch 1: Expired (expired on 2026-08-30)
        b1 = Batch(
            medicine_id=med.id,
            batch_number="B-EXP",
            quantity=30,
            initial_quantity=30,
            expiry_date=date(2026, 8, 30),
        )
        # Batch 2: Expiring in 3 days (2026-09-04) -> within 7 days, should be flagged
        b2 = Batch(
            medicine_id=med.id,
            batch_number="B-CRIT",
            quantity=20,
            initial_quantity=20,
            expiry_date=date(2026, 9, 4),
        )
        # Batch 3: Expiring in 7 days exactly (2026-09-08) -> boundary within 7 days, flagged
        b3 = Batch(
            medicine_id=med.id,
            batch_number="B-7DAY",
            quantity=50,
            initial_quantity=50,
            expiry_date=date(2026, 9, 8),
        )
        # Batch 4: Expiring in 10 days (2026-09-11) -> NOT within 7 days, not flagged
        b4 = Batch(
            medicine_id=med.id,
            batch_number="B-HEALTHY",
            quantity=100,
            initial_quantity=100,
            expiry_date=date(2026, 9, 11),
        )

        db_session.add_all([b1, b2, b3, b4])
        db_session.commit()

        yield
        reset_simulated_today()

    def test_daily_job_quarantines_expired_and_flags_7_days(self):
        current_date = date(2026, 9, 1)
        report = clock_service.run_daily_job(self.db, current_date)

        assert report["quarantined"] >= 1
        assert report["flagged"] == 2  # B-CRIT (3d) and B-7DAY (7d)

        # Verify database fields updated
        b_exp = self.db.query(Batch).filter(Batch.batch_number == "B-EXP").first()
        assert b_exp.is_quarantined is True
        assert "EXPIRED" in (b_exp.quarantine_reason or "")
        assert b_exp.is_flagged is False

        b_crit = self.db.query(Batch).filter(Batch.batch_number == "B-CRIT").first()
        assert b_crit.is_quarantined is False
        assert b_crit.is_flagged is True

        b_7d = self.db.query(Batch).filter(Batch.batch_number == "B-7DAY").first()
        assert b_7d.is_flagged is True

        b_healthy = self.db.query(Batch).filter(Batch.batch_number == "B-HEALTHY").first()
        assert b_healthy.is_flagged is False
        assert b_healthy.is_quarantined is False


class TestClockAPI:
    """Test POST /clock and GET /clock endpoints."""

    def test_post_clock_advances_date_and_returns_counts(self, test_client):
        # Initial call setting date
        resp = test_client.post("/clock", json={"date": "2026-09-15"})
        assert resp.status_code == 200
        data = resp.json()

        assert "date" in data
        assert data["date"] == "2026-09-15"
        assert "quarantined" in data
        assert "flagged" in data

    def test_get_clock_returns_current_simulated_date(self, test_client):
        test_client.post("/clock", json={"date": "2026-10-01"})
        resp = test_client.get("/clock")
        assert resp.status_code == 200
        assert resp.json()["date"] == "2026-10-01"

    def test_clock_quarantine_prevents_dispensing(self, test_client):
        # Create medicine with batch expiring on 2026-09-10
        m_resp = test_client.post("/api/medicines", json={"name": "ClockMed", "sku": "CLK-1"})
        med_id = m_resp.json()["id"]

        test_client.post(f"/api/medicines/{med_id}/batches", json={
            "batch_number": "CLK-B1",
            "quantity": 25,
            "expiry_date": "2026-09-10",
        })

        # Set clock to 2026-09-05: batch is still valid (expires in 5 days)
        test_client.post("/clock", json={"date": "2026-09-05"})
        prev = test_client.post(f"/api/medicines/{med_id}/dispense/preview", json={"quantity": 10})
        assert prev.status_code == 200
        assert prev.json()["feasible"] is True

        # Now advance clock past expiry to 2026-09-11
        adv = test_client.post("/clock", json={"date": "2026-09-11"})
        assert adv.status_code == 200
        assert adv.json()["quarantined"] >= 1

        # Now preview should be infeasible because batch is quarantined/expired!
        prev2 = test_client.post(f"/api/medicines/{med_id}/dispense/preview", json={"quantity": 10})
        assert prev2.status_code == 200
        assert prev2.json()["feasible"] is False
