"""
Seed script — populates the database with realistic demo data.

All expiry dates are RELATIVE TO THE CURRENT DATE so the demo
remains useful regardless of when it is evaluated.

Usage:
    python -m app.seed
"""

from datetime import date, timedelta

from app.database import SessionLocal, init_db
from app.models import (
    Medicine,
    Batch,
    DispenseTransaction,
    DispenseAllocation,
    User,
    UserRole,
)
from app.core.security import hash_password


def seed():
    """Seed the database with demo medicines, batches, and user accounts."""
    init_db()
    db = SessionLocal()

    try:
        # Seed users if they don't exist
        if db.query(User).count() == 0:
            admin_user = User(
                username="admin",
                email="admin@pharmaflow.local",
                hashed_password=hash_password("admin123"),
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            pharmacist_user = User(
                username="pharmacist",
                email="pharmacist@pharmaflow.local",
                hashed_password=hash_password("pharma123"),
                role=UserRole.PHARMACIST.value,
                is_active=True,
            )
            db.add_all([admin_user, pharmacist_user])
            db.commit()
            print("  Created default user accounts: admin (ADMIN), pharmacist (PHARMACIST)")

        # Check if already seeded medicines
        existing = db.query(Medicine).count()
        if existing > 0:
            print(f"Database already has {existing} medicines. Skipping seed.")
            print("Delete pharmaflow.db and re-run to re-seed.")
            return

        today = date.today()

        # ── Medicines ──────────────────────────────────────────
        medicines_data = [
            {
                "name": "Paracetamol",
                "generic_name": "Acetaminophen",
                "manufacturer": "PharmaCorp",
                "strength": "500mg",
                "dosage_form": "Tablet",
                "sku": "PARA-500",
            },
            {
                "name": "Amoxicillin",
                "generic_name": "Amoxicillin",
                "manufacturer": "MediLab",
                "strength": "500mg",
                "dosage_form": "Capsule",
                "sku": "AMOX-500",
            },
            {
                "name": "Cetirizine",
                "generic_name": "Cetirizine Hydrochloride",
                "manufacturer": "AllerCure",
                "strength": "10mg",
                "dosage_form": "Tablet",
                "sku": "CET-10",
            },
            {
                "name": "Azithromycin",
                "generic_name": "Azithromycin",
                "manufacturer": "ZithroHealth",
                "strength": "250mg",
                "dosage_form": "Tablet",
                "sku": "AZITH-250",
            },
            {
                "name": "Ibuprofen",
                "generic_name": "Ibuprofen",
                "manufacturer": "PainRelief Inc",
                "strength": "400mg",
                "dosage_form": "Tablet",
                "sku": "IBU-400",
            },
            {
                "name": "Pantoprazole",
                "generic_name": "Pantoprazole Sodium",
                "manufacturer": "GastroMed",
                "strength": "40mg",
                "dosage_form": "Tablet",
                "sku": "PANTO-40",
            },
        ]

        medicines = []
        for m_data in medicines_data:
            med = Medicine(**m_data)
            db.add(med)
            medicines.append(med)

        db.flush()  # Get IDs

        # ── Batches ────────────────────────────────────────────
        # Paracetamol — the FEFO demo medicine
        paracetamol = medicines[0]
        batches_data = [
            # Expired batch (should never be dispensed)
            {
                "medicine_id": paracetamol.id,
                "batch_number": "PARA-EXPIRED",
                "quantity": 100,
                "initial_quantity": 100,
                "expiry_date": today - timedelta(days=10),
                "received_date": today - timedelta(days=200),
                "purchase_price": 2.50,
                "selling_price": 5.00,
            },
            # Critical — expires in 5 days
            {
                "medicine_id": paracetamol.id,
                "batch_number": "PARA-A",
                "quantity": 20,
                "initial_quantity": 50,
                "expiry_date": today + timedelta(days=5),
                "received_date": today - timedelta(days=100),
                "purchase_price": 2.50,
                "selling_price": 5.00,
            },
            # Expiring soon — 20 days
            {
                "medicine_id": paracetamol.id,
                "batch_number": "PARA-B",
                "quantity": 40,
                "initial_quantity": 80,
                "expiry_date": today + timedelta(days=20),
                "received_date": today - timedelta(days=80),
                "purchase_price": 2.50,
                "selling_price": 5.00,
            },
            # Healthy — 120 days
            {
                "medicine_id": paracetamol.id,
                "batch_number": "PARA-C",
                "quantity": 100,
                "initial_quantity": 100,
                "expiry_date": today + timedelta(days=120),
                "received_date": today - timedelta(days=30),
                "purchase_price": 2.60,
                "selling_price": 5.00,
            },
        ]

        # Amoxicillin
        amoxicillin = medicines[1]
        batches_data.extend([
            {
                "medicine_id": amoxicillin.id,
                "batch_number": "AMOX-001",
                "quantity": 60,
                "initial_quantity": 100,
                "expiry_date": today + timedelta(days=15),
                "received_date": today - timedelta(days=90),
                "purchase_price": 8.00,
                "selling_price": 15.00,
            },
            {
                "medicine_id": amoxicillin.id,
                "batch_number": "AMOX-002",
                "quantity": 150,
                "initial_quantity": 150,
                "expiry_date": today + timedelta(days=180),
                "received_date": today - timedelta(days=20),
                "purchase_price": 7.50,
                "selling_price": 15.00,
            },
        ])

        # Cetirizine
        cetirizine = medicines[2]
        batches_data.extend([
            {
                "medicine_id": cetirizine.id,
                "batch_number": "CET-EXP",
                "quantity": 30,
                "initial_quantity": 50,
                "expiry_date": today - timedelta(days=5),
                "received_date": today - timedelta(days=300),
                "purchase_price": 1.50,
                "selling_price": 3.00,
            },
            {
                "medicine_id": cetirizine.id,
                "batch_number": "CET-001",
                "quantity": 200,
                "initial_quantity": 200,
                "expiry_date": today + timedelta(days=240),
                "received_date": today - timedelta(days=10),
                "purchase_price": 1.50,
                "selling_price": 3.00,
            },
        ])

        # Azithromycin
        azithromycin = medicines[3]
        batches_data.extend([
            {
                "medicine_id": azithromycin.id,
                "batch_number": "AZITH-001",
                "quantity": 30,
                "initial_quantity": 50,
                "expiry_date": today + timedelta(days=3),
                "received_date": today - timedelta(days=150),
                "purchase_price": 12.00,
                "selling_price": 25.00,
            },
            {
                "medicine_id": azithromycin.id,
                "batch_number": "AZITH-002",
                "quantity": 75,
                "initial_quantity": 75,
                "expiry_date": today + timedelta(days=90),
                "received_date": today - timedelta(days=30),
                "purchase_price": 11.00,
                "selling_price": 25.00,
            },
        ])

        # Ibuprofen — all expired (NO_SELLABLE_STOCK demo)
        ibuprofen = medicines[4]
        batches_data.extend([
            {
                "medicine_id": ibuprofen.id,
                "batch_number": "IBU-EXP1",
                "quantity": 45,
                "initial_quantity": 100,
                "expiry_date": today - timedelta(days=30),
                "received_date": today - timedelta(days=365),
                "purchase_price": 3.00,
                "selling_price": 6.00,
            },
            {
                "medicine_id": ibuprofen.id,
                "batch_number": "IBU-EXP2",
                "quantity": 80,
                "initial_quantity": 80,
                "expiry_date": today - timedelta(days=2),
                "received_date": today - timedelta(days=180),
                "purchase_price": 3.00,
                "selling_price": 6.00,
            },
        ])

        # Pantoprazole — zero-quantity batch + healthy batch
        pantoprazole = medicines[5]
        batches_data.extend([
            {
                "medicine_id": pantoprazole.id,
                "batch_number": "PANTO-EMPTY",
                "quantity": 0,
                "initial_quantity": 50,
                "expiry_date": today + timedelta(days=60),
                "received_date": today - timedelta(days=120),
                "purchase_price": 5.00,
                "selling_price": 10.00,
            },
            {
                "medicine_id": pantoprazole.id,
                "batch_number": "PANTO-001",
                "quantity": 120,
                "initial_quantity": 120,
                "expiry_date": today + timedelta(days=200),
                "received_date": today - timedelta(days=15),
                "purchase_price": 4.80,
                "selling_price": 10.00,
            },
        ])

        for b_data in batches_data:
            db.add(Batch(**b_data))

        db.commit()

        print("=" * 60)
        print("  PharmaFlow — Database Seeded Successfully")
        print("=" * 60)
        print(f"  Medicines: {len(medicines)}")
        print(f"  Batches:   {len(batches_data)}")
        print()
        print("  Demo FEFO scenario (Paracetamol 500mg):")
        print(f"    PARA-EXPIRED: 100 units, expired {10} days ago")
        print(f"    PARA-A:        20 units, expires in 5 days (critical)")
        print(f"    PARA-B:        40 units, expires in 20 days (expiring soon)")
        print(f"    PARA-C:       100 units, expires in 120 days (healthy)")
        print(f"    Sellable: 160 | Physical: 260 | Expired: 100")
        print()
        print("  Try dispensing 75 Paracetamol to see FEFO in action!")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
