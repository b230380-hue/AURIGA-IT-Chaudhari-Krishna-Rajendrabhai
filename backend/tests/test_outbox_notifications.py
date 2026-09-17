"""
Tests for Level 3 — T1 (integrate):
When in-date stock for a medicine drops below a threshold, send a re-order alert
via the Notification Service. Graded via /outbox.
"""

from datetime import date
import pytest

from app.models.batch import Batch
from app.models.medicine import Medicine
from app.services import notification_service, clock_service


class TestOutboxNotifications:
    """Test re-order alerts and /outbox endpoint."""

    def test_dispense_triggers_outbox_alert_when_stock_drops_below_threshold(self, test_client):
        # Create medicine with threshold = 20
        m_resp = test_client.post("/api/medicines", json={
            "name": "Insulin Glargine",
            "sku": "INS-100",
        })
        med_id = m_resp.json()["id"]

        # Add batch with 25 units (above threshold 20)
        test_client.post(f"/api/medicines/{med_id}/batches", json={
            "batch_number": "INS-B1",
            "quantity": 25,
            "expiry_date": "2027-01-01",
        })

        # Check outbox initially empty
        outbox_init = test_client.get("/outbox").json()
        assert len(outbox_init) == 0

        # Dispense 10 units -> remaining stock becomes 15 (below threshold 20!)
        disp_resp = test_client.post(f"/api/medicines/{med_id}/dispense", json={"quantity": 10})
        assert disp_resp.status_code == 200

        # Outbox should now contain a reorder alert!
        outbox_after = test_client.get("/outbox").json()
        assert len(outbox_after) >= 1
        alert = outbox_after[0]
        assert alert["medicine_name"] == "Insulin Glargine"
        assert alert["event"] == "REORDER_ALERT"
        assert alert["current_stock"] == 15
        assert alert["threshold"] == 20

    def test_clock_quarantine_triggers_outbox_alert(self, test_client):
        # Create medicine with threshold = 30
        m_resp = test_client.post("/api/medicines", json={
            "name": "Salbutamol",
            "sku": "SALB-1",
        })
        med_id = m_resp.json()["id"]

        # Clear existing outbox messages
        test_client.delete("/outbox")

        # Add batch with 20 units expiring on 2026-09-10
        test_client.post(f"/api/medicines/{med_id}/batches", json={
            "batch_number": "SALB-B1",
            "quantity": 20,
            "expiry_date": "2026-09-10",
        })

        # Advance clock to 2026-09-15 -> batch expires and gets quarantined!
        # Sellable stock drops from 20 to 0 (below threshold 20)
        test_client.post("/clock", json={"date": "2026-09-15"})

        outbox = test_client.get("/outbox").json()
        salb_alerts = [a for a in outbox if a["medicine_name"] == "Salbutamol"]
        assert len(salb_alerts) >= 1
        assert salb_alerts[0]["current_stock"] == 0

    def test_clear_outbox(self, test_client):
        test_client.delete("/outbox")
        outbox = test_client.get("/outbox").json()
        assert len(outbox) == 0
