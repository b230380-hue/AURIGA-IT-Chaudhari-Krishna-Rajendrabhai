"""
Tests for medicine search and alert boundaries.
"""

from datetime import date, timedelta
import pytest

from app.models.batch import Batch
from app.models.medicine import Medicine
from app.services.inventory_service import search_medicines, get_medicine_search_results
from app.services.alert_service import get_expiry_alerts


class TestSearch:
    """Case-insensitive medicine search tests."""

    @pytest.fixture(autouse=True)
    def setup_medicines(self, db_session):
        self.db = db_session
        meds = [
            Medicine(name="Paracetamol", generic_name="Acetaminophen", strength="500mg"),
            Medicine(name="Pantoprazole", generic_name="Pantoprazole Sodium", strength="40mg"),
            Medicine(name="Amoxicillin", generic_name="Amoxicillin", strength="500mg"),
        ]
        for m in meds:
            db_session.add(m)
        db_session.commit()

    def test_search_lowercase(self):
        results = search_medicines(self.db, "para")
        names = [r.name for r in results]
        assert "Paracetamol" in names

    def test_search_uppercase(self):
        results = search_medicines(self.db, "PARA")
        names = [r.name for r in results]
        assert "Paracetamol" in names

    def test_search_mixed_case(self):
        results = search_medicines(self.db, "Paracetamol")
        assert len(results) >= 1

    def test_search_partial(self):
        results = search_medicines(self.db, "amox")
        names = [r.name for r in results]
        assert "Amoxicillin" in names

    def test_search_by_generic_name(self):
        results = search_medicines(self.db, "acetaminophen")
        names = [r.name for r in results]
        assert "Paracetamol" in names

    def test_search_no_results(self):
        results = search_medicines(self.db, "xyzzz")
        assert len(results) == 0

    def test_search_pa_finds_multiple(self):
        """'pa' should match both Paracetamol and Pantoprazole."""
        results = search_medicines(self.db, "pa")
        names = [r.name for r in results]
        assert "Paracetamol" in names
        assert "Pantoprazole" in names


class TestAlertBoundaries:
    """Tests for expiry alert category boundaries."""

    @pytest.fixture
    def alert_medicine(self, db_session, today):
        med = Medicine(name="AlertTest")
        db_session.add(med)
        db_session.flush()

        batches = [
            # Expired (-5 days)
            Batch(medicine_id=med.id, batch_number="ALT-EXP",
                  quantity=10, initial_quantity=10,
                  expiry_date=today - timedelta(days=5)),
            # Expires today (0 days) — CRITICAL
            Batch(medicine_id=med.id, batch_number="ALT-TODAY",
                  quantity=10, initial_quantity=10,
                  expiry_date=today),
            # 7 days — CRITICAL boundary
            Batch(medicine_id=med.id, batch_number="ALT-7D",
                  quantity=10, initial_quantity=10,
                  expiry_date=today + timedelta(days=7)),
            # 8 days — EXPIRING_SOON boundary
            Batch(medicine_id=med.id, batch_number="ALT-8D",
                  quantity=10, initial_quantity=10,
                  expiry_date=today + timedelta(days=8)),
            # 30 days — EXPIRING_SOON boundary
            Batch(medicine_id=med.id, batch_number="ALT-30D",
                  quantity=10, initial_quantity=10,
                  expiry_date=today + timedelta(days=30)),
            # 31 days — HEALTHY (should NOT appear in 30-day alerts)
            Batch(medicine_id=med.id, batch_number="ALT-31D",
                  quantity=10, initial_quantity=10,
                  expiry_date=today + timedelta(days=31)),
        ]
        for b in batches:
            db_session.add(b)
        db_session.commit()
        return med

    def test_alert_categories(self, db_session, alert_medicine, today):
        """Verify correct category assignment at boundaries."""
        alerts = get_expiry_alerts(db_session, threshold_days=30, today=today)

        by_batch = {a.batch_number: a for a in alerts.alerts}

        assert by_batch["ALT-EXP"].status == "EXPIRED"
        assert by_batch["ALT-TODAY"].status == "CRITICAL"
        assert by_batch["ALT-7D"].status == "CRITICAL"
        assert by_batch["ALT-8D"].status == "EXPIRING_SOON"
        assert by_batch["ALT-30D"].status == "EXPIRING_SOON"
        # 31 days should NOT be in 30-day alerts
        assert "ALT-31D" not in by_batch

    def test_alert_sorted_by_urgency(self, db_session, alert_medicine, today):
        """Alerts are sorted by urgency: expired first, then by days remaining."""
        alerts = get_expiry_alerts(db_session, threshold_days=30, today=today)

        statuses = [a.status for a in alerts.alerts]
        # All EXPIRED before CRITICAL before EXPIRING_SOON
        expired_idx = [i for i, s in enumerate(statuses) if s == "EXPIRED"]
        critical_idx = [i for i, s in enumerate(statuses) if s == "CRITICAL"]
        soon_idx = [i for i, s in enumerate(statuses) if s == "EXPIRING_SOON"]

        if expired_idx and critical_idx:
            assert max(expired_idx) < min(critical_idx)
        if critical_idx and soon_idx:
            assert max(critical_idx) < min(soon_idx)

    def test_alert_summary_counts(self, db_session, alert_medicine, today):
        """Alert summary has correct counts."""
        alerts = get_expiry_alerts(db_session, threshold_days=30, today=today)

        assert alerts.summary["EXPIRED"] == 1
        assert alerts.summary["CRITICAL"] == 2  # today + 7 days
        assert alerts.summary["EXPIRING_SOON"] == 2  # 8 days + 30 days

    def test_custom_threshold(self, db_session, alert_medicine, today):
        """Custom threshold of 7 days should only include expired + critical."""
        alerts = get_expiry_alerts(db_session, threshold_days=7, today=today)

        statuses = {a.status for a in alerts.alerts}
        assert "EXPIRED" in statuses
        assert "CRITICAL" in statuses
        # 8-day and 30-day batches should NOT appear
        batch_numbers = {a.batch_number for a in alerts.alerts}
        assert "ALT-8D" not in batch_numbers
        assert "ALT-30D" not in batch_numbers
