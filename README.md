# RecoverAI

AI-powered revenue recovery agent — built for Razorpay AI Revenue Recovery
Track 03.

RecoverAI detects revenue leakage (e.g. failed payments, subscription
churn signals), analyzes the cause, recommends a recovery action, validates
it, executes it, and measures the revenue recovered.

## Pipeline

```
Detect leakage → Analyze → Recommend action → Validate → Execute → Measure recovered revenue
```

## Stack

- **Backend:** Python, FastAPI, PostgreSQL, SQLAlchemy, Pydantic
- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **AI:** local Ollama model (planned, not implemented yet)
- **Data:** Pandas, synthetic data
- **Testing:** Pytest
- **Integration:** Razorpay Test Mode + Webhooks (planned, not implemented yet)

Everything runs free/local — no paid APIs, hosting, or subscriptions.

## Architecture

Modular monolith, kept simple. Backend and frontend are separate apps in
this repo; the backend is organized by concern (`api`, `core`, `db`,
`models`, `schemas`) rather than split into services.

```
Recover-AI/
├── backend/            # FastAPI app
│   ├── app/
│   │   ├── api/        # route handlers
│   │   ├── core/       # config/settings
│   │   ├── data_generation/  # synthetic dataset generator + seed script
│   │   ├── db/         # SQLAlchemy session/base
│   │   ├── models/     # SQLAlchemy models (Customer, Subscription, Payment, RecoveryCase)
│   │   ├── schemas/    # Pydantic schemas
│   │   └── main.py     # app entrypoint
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Next.js app
│   ├── app/
│   └── .env.example
└── README.md
```

## Getting started

### 1. PostgreSQL (local)

Install PostgreSQL locally (e.g. `apt install postgresql` on Debian/Ubuntu,
or `brew install postgresql` on macOS) and create the database and user:

```bash
sudo -u postgres psql -c "CREATE USER recoverai WITH PASSWORD 'recoverai';"
sudo -u postgres psql -c "CREATE DATABASE recoverai OWNER recoverai;"
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000. Health check: `GET /health`.

Run tests:

```bash
pytest
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend runs at http://localhost:3000.

### 4. Synthetic data (seed the database)

Phase 2 adds SQLAlchemy models (`Customer`, `Subscription`, `Payment`,
`RecoveryCase`) and a deterministic synthetic data generator, used later by
the leakage detection and recovery engines. From `backend/`, with the venv
active and `.env` in place:

```bash
python -m app.data_generation.seed
```

This creates the tables (if missing), generates ~1,200 customers, ~400
subscriptions, and 5,000+ payments — covering successful payments,
insufficient funds, temporary failures, timeouts, repeated-retry failures,
subscription payment failures, and abandoned checkouts — and inserts them.
Generation is deterministic (fixed seed), so re-running the command is
safe: rows that already exist (by primary key) are skipped, not duplicated.

Verify the seeded data via the API:

```bash
curl http://localhost:8000/api/data/summary
```

No real customer or payment data is used anywhere — all records are
synthetic and identified only by generated ids.

## Status

**Phase 1:** project scaffolding — backend/frontend skeletons, health
check API, homepage, and local Postgres configuration.

**Phase 2 (current):** database models and a synthetic payment/revenue
dataset (customers, subscriptions, payments, and a `RecoveryCase` schema
placeholder for later phases), plus a duplicate-safe seeding script and a
`/api/data/summary` endpoint to verify the data.

Not implemented yet: AI/Ollama integration, revenue leakage detection,
the recovery engine, Razorpay integration and webhooks, the dashboard,
authentication, and payment execution.
