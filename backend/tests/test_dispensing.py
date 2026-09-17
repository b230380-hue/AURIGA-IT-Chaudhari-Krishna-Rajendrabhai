"""
Tests for the dispensing service — transactional integrity, preview immutability,
and allocation correctness.
"""

from datetime import date, timedelta
import pytest

from app.domain.allocation import InsufficientStockError
from app.models.batch import Batch
from app.models.medicine import Medicine
from app.models.dispense import DispenseTransaction, DispenseAllocation
from app.services.fefo_service import dispense, preview_dispense


@pytest.fixture
def medicine_with_batches(db_session, today):
    """Medicine with mixed batches for dispensing tests."""
    med = Medicine(name="DispenseTest", strength="100mg")
    db_session.add(med)
    db_session.flush()

    batches = [
        Batch(medicine_id=med.id, batch_number="EXP",
              quantity=100, initial_quantity=100,
              expiry_date=today - timedelta(days=5)),  # expired
        Batch(medicine_id=med.id, batch_number="D1",
              quantity=20, initial_quantity=20,
              expiry_date=today + timedelta(days=10)),
        Batch(medicine_id=med.id, batch_number="D2",
              quantity=40, initial_quantity=40,
              expiry_date=today + timedelta(days=30)),
        Batch(medicine_id=med.id, batch_number="D3",
              quantity=100, initial_quantity=100,
              expiry_date=today + timedelta(days=90)),
    ]
    for b in batches:
        db_session.add(b)
    db_session.commit()

    return med, batches


class TestPreviewImmutability:
    """Preview must NEVER modify inventory."""

    def test_preview_does_not_change_quantities(self, db_session, medicine_with_batches, today):
        """After preview, all batch quantities must remain unchanged."""
        med, batches = medicine_with_batches

        # Record quantities before
        before = {b.batch_number: b.quantity for b in batches}

        # Execute preview
        preview = preview_dispense(db_session, med.id, 50, today)

        # Refresh from database
        db_session.expire_all()
        for b in batches:
            db_session.refresh(b)

        # Verify no changes
        after = {b.batch_number: b.quantity for b in batches}
        assert before == after

    def test_preview_shows_correct_allocation(self, db_session, medicine_with_batches, today):
        """Preview returns correct FEFO allocation."""
        med, _ = medicine_with_batches
        preview = preview_dispense(db_session, med.id, 50, today)

        assert preview.feasible is True
        assert preview.requested_quantity == 50
        assert preview.allocation_strategy == "FEFO"
        assert len(preview.allocations) == 2
        assert preview.allocations[0].batch_number == "D1"
        assert preview.allocations[0].quantity_dispensed == 20
        assert preview.allocations[1].batch_number == "D2"
        assert preview.allocations[1].quantity_dispensed == 30

    def test_preview_infeasible(self, db_session, medicine_with_batches, today):
        """Preview correctly reports infeasible for insufficient stock."""
        med, _ = medicine_with_batches
        preview = preview_dispense(db_session, med.id, 999, today)

        assert preview.feasible is False
        assert preview.available_stock == 160  # 20 + 40 + 100

    def test_preview_why_first_batch(self, db_session, medicine_with_batches, today):
        """Preview includes explainability for first batch."""
        med, _ = medicine_with_batches
        preview = preview_dispense(db_session, med.id, 10, today)

        assert preview.why_first_batch is not None
        assert "D1" in preview.why_first_batch


class TestDispenseAtomicity:
    """Dispensing must be atomic — all-or-nothing."""

    def test_insufficient_stock_no_mutation(self, db_session, medicine_with_batches, today):
        """When sellable < requested, no batch quantities should change."""
        med, batches = medicine_with_batches

        before = {b.batch_number: b.quantity for b in batches}

        with pytest.raises(InsufficientStockError) as exc_info:
            dispense(db_session, med.id, 200, today)  # only 160 sellable

        assert exc_info.value.requested == 200
        assert exc_info.value.available == 160

        # Verify absolutely no mutations
        db_session.expire_all()
        for b in batches:
            db_session.refresh(b)
        after = {b.batch_number: b.quantity for b in batches}
        assert before == after

    def test_successful_dispense(self, db_session, medicine_with_batches, today):
        """Successful dispense decrements correctly and creates records."""
        med, batches = medicine_with_batches

        result = dispense(db_session, med.id, 50, today)

        assert result.dispensed_quantity == 50
        assert result.status == "COMPLETED"
        assert len(result.allocations) == 2

        # Verify batch quantities updated
        db_session.expire_all()
        d1 = db_session.query(Batch).filter(Batch.batch_number == "D1").first()
        d2 = db_session.query(Batch).filter(Batch.batch_number == "D2").first()
        exp = db_session.query(Batch).filter(Batch.batch_number == "EXP").first()

        assert d1.quantity == 0   # 20 - 20
        assert d2.quantity == 10  # 40 - 30
        assert exp.quantity == 100  # expired — untouched!

    def test_expired_batch_never_allocated(self, db_session, medicine_with_batches, today):
        """Expired batch must never appear in allocations."""
        med, _ = medicine_with_batches

        result = dispense(db_session, med.id, 10, today)

        for alloc in result.allocations:
            assert alloc.batch_number != "EXP"

    def test_allocation_sum_equals_dispensed(self, db_session, medicine_with_batches, today):
        """Sum of allocation quantities must equal dispensed quantity."""
        med, _ = medicine_with_batches

        result = dispense(db_session, med.id, 75, today)

        total_allocated = sum(a.quantity_dispensed for a in result.allocations)
        assert total_allocated == result.dispensed_quantity == 75

    def test_transaction_record_created(self, db_session, medicine_with_batches, today):
        """Dispense creates transaction and allocation records in DB."""
        med, _ = medicine_with_batches

        result = dispense(db_session, med.id, 30, today)

        txn = db_session.query(DispenseTransaction).filter(
            DispenseTransaction.id == result.transaction_id
        ).first()
        assert txn is not None
        assert txn.requested_quantity == 30
        assert txn.dispensed_quantity == 30
        assert txn.status == "COMPLETED"

        allocs = db_session.query(DispenseAllocation).filter(
            DispenseAllocation.dispense_transaction_id == txn.id
        ).all()
        assert len(allocs) > 0
        assert sum(a.quantity_dispensed for a in allocs) == 30


class TestDispenseEdgeCases:
    """Edge cases for dispensing."""

    def test_invalid_zero_quantity(self, db_session, medicine_with_batches, today):
        """Zero quantity must be rejected."""
        med, _ = medicine_with_batches
        with pytest.raises(ValueError, match="INVALID_QUANTITY"):
            dispense(db_session, med.id, 0, today)

    def test_invalid_negative_quantity(self, db_session, medicine_with_batches, today):
        """Negative quantity must be rejected."""
        med, _ = medicine_with_batches
        with pytest.raises(ValueError, match="INVALID_QUANTITY"):
            dispense(db_session, med.id, -5, today)

    def test_nonexistent_medicine(self, db_session, today):
        """Dispensing from nonexistent medicine must fail."""
        with pytest.raises(ValueError, match="MEDICINE_NOT_FOUND"):
            dispense(db_session, 9999, 10, today)

    def test_exact_sellable_stock(self, db_session, today):
        """Dispensing exactly the sellable amount should succeed."""
        med = Medicine(name="ExactTest")
        db_session.add(med)
        db_session.flush()
        db_session.add(Batch(
            medicine_id=med.id, batch_number="EXACT",
            quantity=50, initial_quantity=50,
            expiry_date=today + timedelta(days=30),
        ))
        db_session.commit()

        result = dispense(db_session, med.id, 50, today)
        assert result.dispensed_quantity == 50
        assert result.remaining_sellable_stock == 0

    def test_dispense_multi_batch_three_plus(self, db_session, today):
        """Dispensing across 3+ batches."""
        med = Medicine(name="MultiTest")
        db_session.add(med)
        db_session.flush()

        for i in range(5):
            db_session.add(Batch(
                medicine_id=med.id, batch_number=f"MB-{i}",
                quantity=10, initial_quantity=10,
                expiry_date=today + timedelta(days=10 + i * 10),
            ))
        db_session.commit()

        result = dispense(db_session, med.id, 35, today)
        assert result.dispensed_quantity == 35
        assert len(result.allocations) == 4  # 10+10+10+5
