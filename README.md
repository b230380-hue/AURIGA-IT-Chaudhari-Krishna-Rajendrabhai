# PharmaFlow

**Expiry-Aware Pharmacy Inventory**

A production-quality pharmacy inventory management application built around one uncompromising principle:

> *Every unit dispensed must come from the safest eligible batch in FEFO order, and an expired unit must never leave inventory through the dispensing workflow.*

---

## Problem Statement

A neighbourhood pharmacy stocks medicines in batches, each with its own expiry date. When dispensing, the pharmacy must:

1. **Use the batch that expires soonest first** (FEFO — First Expiry, First Out)
2. **Never dispense an expired batch**
3. **Know the sellable stock** (ignoring expired batches)
4. **Answer "do we have paracetamol in date?"** quickly
5. **Get alerts on batches about to expire**

PharmaFlow solves all of these with a clean, transactional, auditable system.

---

## Features

### Core (P0)
- ✅ Medicine management (CRUD, search)
- ✅ Batch management with expiry tracking
- ✅ **FEFO dispensing** — automatic first-expiry-first-out allocation
- ✅ **Expiry protection** — expired batches are never dispensed
- ✅ **Sellable stock calculation** — expired inventory excluded
- ✅ **Negative stock prevention** — check constraints + pre-validation
- ✅ **Atomic transactions** — all-or-nothing dispensing
- ✅ **Complete allocation records** — traceability of every batch consumed
- ✅ **Comprehensive tests** — all core business rules verified

### Enhanced (P1)
- ✅ Case-insensitive medicine search
- ✅ Availability query with stock status
- ✅ Expiry alerts (7/30/60/90 day thresholds)
- ✅ Pharmacy dashboard with summary cards
- ✅ Dispensing history with allocation details
- ✅ Batch-level auditability

### Polish (P2)
- ✅ Inventory health score (deterministic, transparent)
- ✅ Expiry risk/waste exposure metrics
- ✅ FEFO queue visualization
- ✅ FEFO preview with "Why this batch?" explainability
- ✅ Multi-step dispensing workflow
- ✅ Responsive, accessible UI

---

## Architecture

```
PharmaFlow/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Pydantic settings
│   │   ├── database.py        # SQLAlchemy engine & session
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── domain/            # Pure business logic
│   │   │   ├── expiry.py      # Centralized expiry semantics
│   │   │   └── allocation.py  # FEFO allocation algorithm
│   │   ├── services/          # Business service layer
│   │   │   ├── inventory_service.py
│   │   │   ├── fefo_service.py
│   │   │   ├── alert_service.py
│   │   │   └── dashboard_service.py
│   │   ├── api/               # REST API route handlers
│   │   └── seed.py            # Demo data seeder
│   ├── tests/                 # pytest test suite
│   └── requirements.txt
├── frontend/                   # React + Vite + TypeScript
│   └── src/
│       ├── api/               # API client (Axios)
│       ├── components/        # Layout, Sidebar
│       ├── pages/             # Dashboard, Medicines, Dispense, Alerts, Transactions
│       ├── types/             # TypeScript interfaces
│       └── utils/             # Helpers
└── README.md
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.x, Pydantic v2 |
| Database | SQLite (PostgreSQL-ready architecture) |
| Testing | pytest, httpx (TestClient) |
| Frontend | React 18, Vite, TypeScript, React Router |
| HTTP Client | Axios |
| Icons | Lucide React |

---

## Database Schema

### Medicine
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, auto-increment |
| name | VARCHAR(255) | NOT NULL, indexed |
| generic_name | VARCHAR(255) | nullable |
| manufacturer | VARCHAR(255) | nullable |
| strength | VARCHAR(100) | nullable |
| dosage_form | VARCHAR(100) | nullable |
| sku | VARCHAR(100) | UNIQUE, nullable |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

### Batch
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK, auto-increment |
| medicine_id | INTEGER | FK → medicines.id, NOT NULL |
| batch_number | VARCHAR(100) | NOT NULL |
| quantity | INTEGER | NOT NULL, CHECK ≥ 0 |
| initial_quantity | INTEGER | NOT NULL, CHECK ≥ 0 |
| expiry_date | DATE | NOT NULL, indexed |
| received_date | DATE | nullable |
| purchase_price | FLOAT | nullable |
| selling_price | FLOAT | nullable |
| created_at | DATETIME | NOT NULL |
| updated_at | DATETIME | NOT NULL |

**Composite index:** `(medicine_id, expiry_date)` — optimizes FEFO queries.

### DispenseTransaction
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK |
| medicine_id | INTEGER | FK → medicines.id |
| requested_quantity | INTEGER | CHECK > 0 |
| dispensed_quantity | INTEGER | CHECK ≥ 0 |
| status | VARCHAR(20) | COMPLETED / FAILED |
| created_at | DATETIME | |

### DispenseAllocation
| Column | Type | Constraints |
|--------|------|------------|
| id | INTEGER | PK |
| dispense_transaction_id | INTEGER | FK → dispense_transactions.id |
| batch_id | INTEGER | FK → batches.id |
| quantity_dispensed | INTEGER | CHECK > 0 |
| batch_expiry_date_snapshot | DATE | |
| created_at | DATETIME | |

---

## FEFO Algorithm

**FEFO = First Expiry, First Out**

The core allocation algorithm lives in `backend/app/domain/allocation.py` and is a **pure function** shared by both preview and actual dispensing:

```
1. Filter eligible batches: quantity > 0 AND expiry_date >= today
2. Sort by: expiry_date ASC, received_date ASC, id ASC
3. Calculate total sellable stock
4. If sellable < requested → REJECT (zero mutations)
5. Allocate sequentially from earliest-expiring
6. Return allocation plan
```

**Key design decisions:**
- Preview and dispense use the **same `plan_fefo_allocation()` function** — no duplicated logic
- Availability is checked **before** any mutations
- If insufficient stock, the operation is rejected with **zero side effects**
- Tie-breaking is deterministic: `expiry_date → received_date → id`

### Why FEFO instead of FIFO?

**FIFO** (First In, First Out) prioritizes by arrival order. A batch received earlier is dispensed first regardless of when it expires.

**FEFO** (First Expiry, First Out) prioritizes by expiry date. The batch closest to expiring is dispensed first.

For expiry-sensitive inventory like medicine, **FEFO is the correct strategy** because:
- A batch received last week might expire sooner than one received last month
- FEFO minimizes waste by ensuring near-expiry stock is consumed first
- Regulatory guidance for pharmaceuticals typically recommends FEFO

---

## Expiry Semantics

Defined in `backend/app/domain/expiry.py`:

| Condition | Rule |
|-----------|------|
| **Expired** | `expiry_date < today` |
| **Sellable** | `expiry_date >= today AND quantity > 0` |
| **Critical** | 0–7 days remaining |
| **Expiring Soon** | 8–30 days remaining |
| **Healthy** | >30 days remaining |

**Important:** A batch remains valid **through** its printed expiry date (it becomes expired **after** that date). This is the standard pharmacy interpretation.

The "today" reference date is injectable for deterministic testing.

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/medicines` | List all medicines |
| POST | `/api/medicines` | Create medicine |
| GET | `/api/medicines/{id}` | Get medicine |
| PUT | `/api/medicines/{id}` | Update medicine |
| GET | `/api/medicines/search?q=` | Search medicines with availability |
| GET | `/api/medicines/{id}/batches` | List batches with FEFO priority |
| POST | `/api/medicines/{id}/batches` | Add batch |
| GET | `/api/medicines/{id}/stock` | Get stock summary |
| POST | `/api/medicines/{id}/dispense/preview` | FEFO preview (read-only) |
| POST | `/api/medicines/{id}/dispense` | Execute dispense (atomic) |
| GET | `/api/alerts/expiry?days=30` | Expiry alerts |
| GET | `/api/dispenses` | Dispense history |
| GET | `/api/dispenses/{id}` | Transaction detail |
| GET | `/api/dashboard` | Dashboard aggregation |

Interactive API docs: `http://localhost:8000/docs`

---

## Safety Guarantees

1. **Expired batches excluded** — never allocated during dispensing
2. **Insufficient stock = atomic rejection** — zero mutations on failure
3. **Negative stock prevented** — CHECK constraints + pre-validation
4. **Deterministic FEFO ordering** — expiry → received → id
5. **Allocation history retained** — every batch contribution recorded
6. **Preview never mutates** — read-only allocation planning

---

## Installation & Running

### Prerequisites
- Python 3.12+
- Node.js 18+
- npm

### Backend

```bash
cd backend
python -m venv .venv

# Linux/macOS:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
python -m app.seed          # Load demo data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Open: `http://localhost:5173`  
API docs: `http://localhost:8000/docs`

### GitHub Codespaces

```bash
# Terminal 1 — Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

> **Note:** In Codespaces, update `frontend/.env` to point `VITE_API_URL` to the Codespace-forwarded backend URL if needed.

---

## Testing

```bash
cd backend
.venv/bin/pytest tests/ -v    # or .venv\Scripts\pytest tests/ -v on Windows
```

### Test Coverage

| Test File | Covers |
|-----------|--------|
| `test_expiry.py` | Expiry semantics, boundary conditions, mutual exclusivity |
| `test_fefo.py` | FEFO allocation: ordering, expired exclusion, tie-breaking, edge cases |
| `test_stock.py` | Sellable stock calculation, expired exclusion, zero-quantity handling |
| `test_dispensing.py` | Atomic dispensing, preview immutability, allocation integrity |
| `test_search_alerts.py` | Case-insensitive search, alert boundaries, category correctness |
| `test_api.py` | API integration: CRUD, dispense, alerts, dashboard |

---

## Demo Walkthrough

### Seeded Data

The seed creates 6 medicines with realistic batches:

**Paracetamol 500mg** (FEFO demo):
- `PARA-EXPIRED`: 100 units, expired 10 days ago → **EXCLUDED from sellable**
- `PARA-A`: 20 units, expires in 5 days → **FEFO #1 (Critical)**
- `PARA-B`: 40 units, expires in 20 days → **FEFO #2 (Expiring Soon)**
- `PARA-C`: 100 units, expires in 120 days → **FEFO #3 (Healthy)**

**Sellable: 160 | Physical: 260 | Expired: 100**

### Dispense 75 Paracetamol (FEFO Demo)

1. Navigate to **Dispense** → search "Paracetamol"
2. Enter quantity: **75**
3. Click **Preview FEFO Allocation**
4. See: PARA-A → 20, PARA-B → 40, PARA-C → 15
5. Note: PARA-EXPIRED is **excluded** (expired)
6. Click **Confirm Dispense**
7. Receipt shows allocation across 3 batches
8. Remaining sellable: **85**

### Ibuprofen (No Sellable Stock)
All batches expired → shows "No Sellable Stock" status despite physical inventory existing.

---

## Design Decisions

1. **Pure allocation function** — `plan_fefo_allocation()` is side-effect-free, enabling shared use by preview and dispense
2. **Injectable "today"** — all date comparisons use an injectable reference date for deterministic testing
3. **Centralized expiry semantics** — single source of truth in `domain/expiry.py`
4. **Allocation records** — every dispense is fully traceable to specific batches
5. **Physical vs sellable stock** — clear separation; expired inventory is retained for record-keeping
6. **SQLite with PostgreSQL-ready design** — no SQLite-specific business logic; migration straightforward

## Concurrency Note

SQLite provides serialized access which is adequate for single-pharmacy use. For high-concurrency production deployment:
- Migrate to PostgreSQL
- Use `SELECT ... FOR UPDATE` row-level locking on batches during dispensing
- Consider optimistic concurrency with version columns

## Assumptions

- Dispensing is always full-fill (no partial dispense on insufficient stock)
- Batch numbers are informational (not globally unique across medicines)
- Expiry dates are date-only (no time component)
- Single-pharmacy deployment (no multi-tenant)

---

*Built with care for pharmacy safety and software correctness.*
