"""
API integration tests using FastAPI TestClient.
"""

from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.medicine import Medicine
from app.models.batch import Batch


@pytest.fixture
def test_client():
    """Create test client with isolated database."""
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


class TestHealthEndpoint:
    def test_health(self, test_client):
        resp = test_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestMedicineAPI:
    def test_create_medicine(self, test_client):
        resp = test_client.post("/api/medicines", json={
            "name": "Paracetamol",
            "strength": "500mg",
            "dosage_form": "Tablet",
            "sku": "PARA-500",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Paracetamol"
        assert data["sku"] == "PARA-500"

    def test_duplicate_sku_rejected(self, test_client):
        test_client.post("/api/medicines", json={
            "name": "Med1", "sku": "DUP-SKU",
        })
        resp = test_client.post("/api/medicines", json={
            "name": "Med2", "sku": "DUP-SKU",
        })
        assert resp.status_code == 409
        assert "DUPLICATE_SKU" in resp.json()["detail"]["error"]

    def test_list_medicines(self, test_client):
        test_client.post("/api/medicines", json={"name": "TestMed"})
        resp = test_client.get("/api/medicines")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_medicine_not_found(self, test_client):
        resp = test_client.get("/api/medicines/999")
        assert resp.status_code == 404

    def test_search_medicines(self, test_client):
        test_client.post("/api/medicines", json={"name": "Paracetamol"})
        resp = test_client.get("/api/medicines/search", params={"q": "para"})
        assert resp.status_code == 200
        results = resp.json()
        assert any(r["name"] == "Paracetamol" for r in results)


class TestBatchAPI:
    def test_create_batch(self, test_client):
        # Create medicine first
        med_resp = test_client.post("/api/medicines", json={"name": "BatchTest"})
        med_id = med_resp.json()["id"]

        resp = test_client.post(f"/api/medicines/{med_id}/batches", json={
            "batch_number": "BT-001",
            "quantity": 100,
            "expiry_date": (date.today() + timedelta(days=90)).isoformat(),
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["batch_number"] == "BT-001"
        assert data["quantity"] == 100

    def test_batch_for_nonexistent_medicine(self, test_client):
        resp = test_client.post("/api/medicines/999/batches", json={
            "batch_number": "X",
            "quantity": 10,
            "expiry_date": "2027-01-01",
        })
        assert resp.status_code == 404


class TestDispenseAPI:
    @pytest.fixture(autouse=True)
    def setup_dispense_data(self, test_client):
        self.client = test_client

        # Create medicine
        resp = test_client.post("/api/medicines", json={
            "name": "DispenseAPI",
            "strength": "100mg",
        })
        self.med_id = resp.json()["id"]

        today = date.today()

        # Add batches
        test_client.post(f"/api/medicines/{self.med_id}/batches", json={
            "batch_number": "API-1",
            "quantity": 30,
            "expiry_date": (today + timedelta(days=15)).isoformat(),
        })
        test_client.post(f"/api/medicines/{self.med_id}/batches", json={
            "batch_number": "API-2",
            "quantity": 50,
            "expiry_date": (today + timedelta(days=60)).isoformat(),
        })

    def test_dispense_preview(self):
        resp = self.client.post(
            f"/api/medicines/{self.med_id}/dispense/preview",
            json={"quantity": 40},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["feasible"] is True
        assert data["allocation_strategy"] == "FEFO"
        assert data["allocations"][0]["batch_number"] == "API-1"

    def test_dispense_execute(self):
        resp = self.client.post(
            f"/api/medicines/{self.med_id}/dispense",
            json={"quantity": 40},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dispensed_quantity"] == 40
        assert data["status"] == "COMPLETED"
        assert sum(a["quantity_dispensed"] for a in data["allocations"]) == 40

    def test_dispense_insufficient(self):
        resp = self.client.post(
            f"/api/medicines/{self.med_id}/dispense",
            json={"quantity": 999},
        )
        assert resp.status_code == 409
        assert "INSUFFICIENT_SELLABLE_STOCK" in resp.json()["detail"]["error"]

    def test_dispense_zero_quantity(self):
        resp = self.client.post(
            f"/api/medicines/{self.med_id}/dispense",
            json={"quantity": 0},
        )
        assert resp.status_code == 422  # Pydantic validation

    def test_dispense_history(self):
        # Dispense first
        self.client.post(
            f"/api/medicines/{self.med_id}/dispense",
            json={"quantity": 10},
        )
        resp = self.client.get("/api/dispenses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1


class TestStockAPI:
    def test_stock_endpoint(self, test_client):
        med_resp = test_client.post("/api/medicines", json={"name": "StockTest"})
        med_id = med_resp.json()["id"]

        today = date.today()
        test_client.post(f"/api/medicines/{med_id}/batches", json={
            "batch_number": "ST-1",
            "quantity": 50,
            "expiry_date": (today + timedelta(days=30)).isoformat(),
        })

        resp = test_client.get(f"/api/medicines/{med_id}/stock")
        assert resp.status_code == 200
        data = resp.json()
        assert data["sellable_stock"] == 50
        assert data["physical_stock"] == 50


class TestAlertsAPI:
    def test_alerts_endpoint(self, test_client):
        resp = test_client.get("/api/alerts/expiry", params={"days": 30})
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "summary" in data


class TestDashboardAPI:
    def test_dashboard_endpoint(self, test_client):
        resp = test_client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "health" in data
        assert "fefo_queue" in data
