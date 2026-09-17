"""
Tests for sellable stock calculations and inventory queries.
"""

from datetime import date, timedelta
import pytest

from app.models.batch import Batch
from app.models.medicine import Medicine
from app.services.inventory_service import get_medicine_stock


class TestSellableStock:
    """Tests for sellable stock calculation."""

    def test_sellable_excludes_expired(self, db_session, today):
        """Expired batches must not contribute to sellable stock."""
        med = Medicine(name="Test", strength="100mg")
        db_session.add(med)
        db_session.flush()

        # 50 expired + 100 valid + 75 valid = 175 sellable
        batches = [
            Batch(medicine_id=med.id, batch_number="A",
                  quantity=50, initial_quantity=50,
                  expiry_date=today - timedelta(days=1)),  # expired
            Batch(medicine_id=med.id, batch_number="B",
                  quantity=100, initial_quantity=100,
                  expiry_date=today + timedelta(days=30)),
            Batch(medicine_id=med.id, batch_number="C",
                  quantity=75, initial_quantity=75,
                  expiry_date=today + timedelta(days=60)),
        ]
        for b in batches:
            db_session.add(b)
        db_session.commit()

        stock = get_medicine_stock(db_session, med.id, today)

        assert stock.physical_stock == 225
        assert stock.expired_stock == 50
        assert stock.sellable_stock == 175

    def test_sellable_with_all_expired(self, db_session, today):
        """If all batches expired, sellable = 0."""
        med = Medicine(name="AllExpired")
        db_session.add(med)
        db_session.flush()

        db_session.add(Batch(
            medicine_id=med.id, batch_number="EXP",
            quantity=100, initial_quantity=100,
            expiry_date=today - timedelta(days=5),
        ))
        db_session.commit()

        stock = get_medicine_stock(db_session, med.id, today)
        assert stock.sellable_stock == 0
        assert stock.expired_stock == 100
        assert stock.physical_stock == 100

    def test_sellable_with_zero_quantity_batches(self, db_session, today):
        """Zero-quantity valid batches don't contribute to sellable."""
        med = Medicine(name="ZeroTest")
        db_session.add(med)
        db_session.flush()

        db_session.add(Batch(
            medicine_id=med.id, batch_number="ZERO",
            quantity=0, initial_quantity=50,
            expiry_date=today + timedelta(days=30),
        ))
        db_session.add(Batch(
            medicine_id=med.id, batch_number="FULL",
            quantity=40, initial_quantity=40,
            expiry_date=today + timedelta(days=60),
        ))
        db_session.commit()

        stock = get_medicine_stock(db_session, med.id, today)
        assert stock.sellable_stock == 40

    def test_expires_today_counted_as_sellable(self, db_session, today):
        """Batch expiring today is still sellable."""
        med = Medicine(name="TodayTest")
        db_session.add(med)
        db_session.flush()

        db_session.add(Batch(
            medicine_id=med.id, batch_number="TODAY",
            quantity=25, initial_quantity=25,
            expiry_date=today,
        ))
        db_session.commit()

        stock = get_medicine_stock(db_session, med.id, today)
        assert stock.sellable_stock == 25
        assert stock.expired_stock == 0

    def test_next_expiry_tracks_nearest_valid(self, db_session, today):
        """next_expiry_date should show the nearest non-expired batch."""
        med = Medicine(name="NextExpiry")
        db_session.add(med)
        db_session.flush()

        db_session.add(Batch(
            medicine_id=med.id, batch_number="NEAR",
            quantity=10, initial_quantity=10,
            expiry_date=today + timedelta(days=5),
        ))
        db_session.add(Batch(
            medicine_id=med.id, batch_number="FAR",
            quantity=50, initial_quantity=50,
            expiry_date=today + timedelta(days=100),
        ))
        db_session.commit()

        stock = get_medicine_stock(db_session, med.id, today)
        assert stock.next_expiry_date == (today + timedelta(days=5)).isoformat()
        assert stock.next_expiry_days == 5

    def test_expiring_soon_stock_counted(self, db_session, today):
        """Stock in CRITICAL and EXPIRING_SOON batches is counted."""
        med = Medicine(name="SoonTest")
        db_session.add(med)
        db_session.flush()

        db_session.add(Batch(
            medicine_id=med.id, batch_number="CRIT",
            quantity=10, initial_quantity=10,
            expiry_date=today + timedelta(days=3),  # critical
        ))
        db_session.add(Batch(
            medicine_id=med.id, batch_number="SOON",
            quantity=20, initial_quantity=20,
            expiry_date=today + timedelta(days=15),  # expiring soon
        ))
        db_session.add(Batch(
            medicine_id=med.id, batch_number="SAFE",
            quantity=100, initial_quantity=100,
            expiry_date=today + timedelta(days=180),  # healthy
        ))
        db_session.commit()

        stock = get_medicine_stock(db_session, med.id, today)
        assert stock.expiring_soon_stock == 30  # 10 + 20
        assert stock.sellable_stock == 130
