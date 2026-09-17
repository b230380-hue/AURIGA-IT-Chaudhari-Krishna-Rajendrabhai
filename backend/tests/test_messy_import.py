"""
Tests for Level 2 — T4 (messy data):
Import messy batch list (nulls, '10 units', dd/mm/yyyy vs ISO dates, duplicate rows)
into correct stock with an { imported, deduped, rejected } report.
"""

import pytest
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.services import import_service


class TestMessyDataImport:
    """Test importing messy batches via import_service and API."""

    def test_clean_quantity_variations(self):
        assert import_service._clean_quantity("10 units") == 10
        assert import_service._clean_quantity(" 25 boxes ") == 25
        assert import_service._clean_quantity(100) == 100
        assert import_service._clean_quantity("50") == 50
        assert import_service._clean_quantity(None) is None
        assert import_service._clean_quantity("invalid") is None
        assert import_service._clean_quantity(-5) is None

    def test_clean_date_variations(self):
        from datetime import date
        # ISO
        assert import_service._clean_date("2026-12-25") == date(2026, 12, 25)
        # European DD/MM/YYYY
        assert import_service._clean_date("25/12/2026") == date(2026, 12, 25)
        # European DD-MM-YYYY
        assert import_service._clean_date("25-12-2026") == date(2026, 12, 25)
        # Null / invalid
        assert import_service._clean_date(None) is None
        assert import_service._clean_date("invalid-date") is None

    def test_import_messy_batches_service(self, db_session):
        data = [
            # 1. Valid messy row ('10 units', dd/mm/yyyy)
            {
                "medicine_name": "Ibuprofen",
                "batch_number": "IBU-M1",
                "quantity": "10 units",
                "expiry_date": "15/11/2026",
            },
            # 2. Duplicate row of row 1 (should be deduped)
            {
                "medicine_name": "Ibuprofen",
                "batch_number": "IBU-M1",
                "quantity": "20 units",
                "expiry_date": "15/11/2026",
            },
            # 3. Missing medicine name (null) -> rejected
            {
                "medicine_name": None,
                "batch_number": "B-NONAME",
                "quantity": "50 units",
                "expiry_date": "2026-12-01",
            },
            # 4. Missing batch number -> rejected
            {
                "medicine_name": "Paracetamol",
                "batch_number": "",
                "quantity": "100",
                "expiry_date": "2027-01-01",
            },
            # 5. Invalid quantity ('no units') -> rejected
            {
                "medicine_name": "Paracetamol",
                "batch_number": "PARA-BADQTY",
                "quantity": "no units",
                "expiry_date": "2027-01-01",
            },
            # 6. Valid row with ISO date
            {
                "medicine_name": "Paracetamol",
                "batch_number": "PARA-M2",
                "quantity": " 45 boxes ",
                "expiry_date": "2027-03-20",
            },
        ]

        report = import_service.import_batches(db_session, data)

        assert report["imported"] == 2  # IBU-M1 and PARA-M2
        assert report["deduped"] == 1   # Second IBU-M1
        assert report["rejected"] == 3  # null med, empty batch, invalid qty
        assert len(report["errors"]) == 3

    def test_import_endpoint_post_batches_import(self, test_client):
        payload = [
            {
                "medicine": "Amoxicillin",
                "batch": "AMOX-IMP1",
                "qty": "30 tabs",
                "expiry": "01/06/2027",
            },
            {
                "medicine": "Amoxicillin",
                "batch": "AMOX-IMP1",
                "qty": "10 tabs",
                "expiry": "01/06/2027",
            },
            {
                "medicine": "Amoxicillin",
                "batch": "AMOX-BAD",
                "qty": "invalid",
                "expiry": "01/06/2027",
            },
        ]

        resp = test_client.post("/batches/import", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["imported"] == 1
        assert data["deduped"] == 1
        assert data["rejected"] == 1
