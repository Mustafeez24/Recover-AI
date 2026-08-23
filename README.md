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
│   │   ├── recovery/   # deterministic revenue-leakage detection engine
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

### 5. Revenue leakage detection

**Revenue leakage** is money a business should have collected but didn't
because a payment failed, timed out, or was abandoned. Not every leaked
payment is worth chasing, though — some are already lost causes (excessive
retries, a canceled subscription). The Phase 3 detection engine looks at
every payment in the database and, using only plain deterministic rules
(no ML, no LLM), decides:

1. **Is it a valid recovery opportunity at all** (eligibility)?
2. **If so, how urgent is it** (HIGH/MEDIUM/LOW priority)?
3. **What kind of failure is it** (for Phase 4 to pick a strategy)?

It only *identifies and prioritizes* opportunities — it never decides or
executes the actual recovery action; that's Phase 4's job.

#### Eligibility rules

A payment is **not** a recovery opportunity when:
- it already succeeded (`payment_status == success`) — nothing to recover
- it has been retried 4+ times (`retry_count >= 4`) — recovery attempts
  are considered exhausted, further automated retries aren't attempted
- it belongs to a subscription that's already `canceled` — recovery no
  longer applies

Everything else with `payment_status` in `failed` / `timeout` / `abandoned`
is eligible.

#### Failure categories

Each eligible payment is assigned exactly one category (checked in this
order, so a payment only ever lands in one bucket):

| Order | Category | Condition |
|---|---|---|
| 1 | `abandoned_checkout` | `payment_status == abandoned` |
| 2 | `payment_timeout` | `payment_status == timeout` |
| 3 | `repeated_failure` | `retry_count >= 2` |
| 4 | `subscription_failure` | tied to a subscription |
| 5 | `insufficient_funds` | `failure_reason == insufficient_funds` |
| 6 | `temporary_failure` | everything else |

#### Priority logic (deterministic point score)

| Factor | Points |
|---|---|
| Amount ≥ ₹2,000 | +2 |
| Amount ≥ ₹500 | +1 |
| Customer success rate ≥ 70% | +2 |
| Customer success rate ≥ 40% | +1 |
| Failure category is actionable (always true for eligible cases) | +1 |
| No retry attempted yet (`retry_count == 0`) | +1 |
| Already retried 3+ times | -1 |

Score ≥ 5 → **HIGH**, score ≥ 3 → **MEDIUM**, otherwise **LOW**. Every
factor that contributed is recorded in plain English in
`detection_reason`, so every decision is auditable.

#### Duplicate-safe / idempotent

`recovery_cases.payment_id` is unique, and detection checks existing
cases before creating new ones — running detection any number of times
never creates duplicate opportunities.

#### API usage

```bash
# Run detection (safe to call repeatedly)
curl -X POST http://localhost:8000/api/recovery/detect

# List opportunities, with optional filters
curl "http://localhost:8000/api/recovery/opportunities?priority=high&min_amount=1000&limit=10"

# One opportunity with its supporting payment/customer info
curl http://localhost:8000/api/recovery/opportunities/rec_pay_sub_004595

# Live summary metrics
curl http://localhost:8000/api/recovery/summary
```

Filters on `GET /api/recovery/opportunities`: `priority`, `status`,
`failure_category`, `min_amount`, `max_amount`, plus `limit`/`offset`
pagination.

Example opportunity:

```json
{
  "recovery_case_id": "rec_pay_sub_004595",
  "payment_id": "pay_sub_004595",
  "customer_id": "cus_01194",
  "status": "open",
  "priority": "high",
  "amount_at_risk": 2999.0,
  "customer_value": 35988.0,
  "failure_category": "subscription_failure",
  "detection_reason": "HIGH priority subscription failure: high-value payment (₹2999.00); strong customer payment history (86% success rate); subscription failure is typically actionable.",
  "recommended_next_step": "retry_subscription_payment",
  "created_at": "2026-08-23T18:03:13.065981"
}
```

## Status

**Phase 1:** project scaffolding — backend/frontend skeletons, health
check API, homepage, and local Postgres configuration.

**Phase 2:** database models and a synthetic payment/revenue dataset
(customers, subscriptions, payments), plus a duplicate-safe seeding
script and a `/api/data/summary` endpoint to verify the data.

**Phase 3 (current):** a deterministic revenue leakage detection engine
that analyzes payments and creates prioritized `RecoveryCase` records
(rule-based eligibility, HIGH/MEDIUM/LOW priority, no ML/LLM), plus
`/api/recovery/detect`, `/opportunities`, `/opportunities/{id}`, and
`/summary` endpoints.

Not implemented yet: AI/Ollama integration, the recovery action/state
machine, Razorpay integration and webhooks, the dashboard, authentication,
and payment execution.
