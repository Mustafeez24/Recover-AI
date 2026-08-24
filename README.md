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
- **AI:** local Ollama (Qwen 2.5 3B) — advisory recommendations only
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
│   │   ├── ai/          # AI provider abstraction + Ollama + safety-gated service
│   │   ├── api/         # route handlers
│   │   ├── core/        # config/settings
│   │   ├── data_generation/  # synthetic dataset generator + seed script
│   │   ├── db/          # SQLAlchemy session/base + migration scripts
│   │   ├── models/      # SQLAlchemy models (Customer, Subscription, Payment, RecoveryCase, RecoveryActionHistory, AIRecommendation)
│   │   ├── recovery/    # deterministic detection + recovery action engine
│   │   ├── schemas/     # Pydantic schemas
│   │   └── main.py      # app entrypoint
│   ├── scripts/         # standalone verification scripts (e.g. live Ollama check)
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # Next.js app (App Router + TypeScript + Tailwind)
│   ├── app/             # pages: dashboard, opportunities, opportunities/[id], ai
│   ├── components/      # shared UI (nav, banner, badges, charts, buttons)
│   ├── lib/             # typed API client, React Query hooks, formatters
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

Frontend runs at http://localhost:3000 — the Phase 6 dashboard (see §8
below). It talks to the backend at `NEXT_PUBLIC_API_BASE_URL`
(`.env.example` defaults to `http://localhost:8000`); the backend must be
running first.

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
  "status": "detected",
  "priority": "high",
  "amount_at_risk": 2999.0,
  "customer_value": 35988.0,
  "failure_category": "subscription_failure",
  "detection_reason": "HIGH priority subscription failure: high-value payment (₹2999.00); strong customer payment history (86% success rate); subscription failure is typically actionable.",
  "recommended_next_step": "retry_subscription_payment",
  "created_at": "2026-08-23T18:03:13.065981"
}
```

### 6. Recovery actions (simulated -- no real money ever moves)

Phase 4 takes each recovery opportunity Phase 3 found and decides the
safest **bounded action** to take, validates that it's actually safe to
run, and then **simulates** running it locally. Nothing here ever calls
Razorpay or moves real money — `execute` only ever writes to the local
database.

```
Recovery Opportunity → Action Eligibility → Action Selection → Safety
Validation → Execute (simulated) → Update Recovery Case → Record Result
```

#### Recovery action types

| Action | Meaning |
|---|---|
| `retry_payment` | Attempt the payment again right now |
| `schedule_retry` | Defer to a later retry rather than trying again immediately |
| `send_payment_reminder` | Nudge the customer, don't touch the payment method |
| `request_payment_method_update` | Ask the customer to fix/replace their payment method |
| `escalate` | Hand off to manual review — the safe fallback whenever automation looks risky |

#### Action-selection rules (deterministic, one action per case)

| Failure category | Rule |
|---|---|
| `abandoned_checkout` | Always `send_payment_reminder` |
| `temporary_failure` | `retry_payment` |
| `payment_timeout` | `retry_payment` on the first attempt, else `schedule_retry` |
| `insufficient_funds` | `schedule_retry` if priority is HIGH, else `send_payment_reminder` |
| `subscription_failure` | `escalate` if the subscription is already canceled; `retry_payment` on the first attempt; else `request_payment_method_update` |
| `repeated_failure` | `escalate` if amount ≥ ₹5,000 or customer success rate < 40%; else `request_payment_method_update` |

Two safety overrides apply before any of the above: a payment already
retried 4+ times, or a case that's already gone through 3 automated
recovery attempts, is escalated rather than attempted again. Every
selection comes with a plain-English reason (`action_reason`).

#### Safety validation (runs before every execution)

An action is rejected — never silently run — if: the payment already
succeeded, the case is already `recovered` / `escalated` / `exhausted`,
the retry limit has been reached, the subscription is canceled and the
action would retry anyway, the action isn't semantically valid for the
case's failure category, or required payment/case data is missing.

#### State machine

```
DETECTED → PLANNED → VALIDATED → EXECUTING → RECOVERED
                ↓                     ↓  ↓
              FAILED ←────────────────┘  └→ ESCALATED
             ↙  ↓  ↘
      PLANNED  ESCALATED  EXHAUSTED
```

`PLANNED → FAILED` happens when validation rejects the planned action.
`EXECUTING → ESCALATED` happens when the executed action was itself
`escalate`. A `FAILED` case can be re-planned (retry loop) up to 3 times
before it's marked `EXHAUSTED`, or escalated directly if the underlying
payment's own retry limit is hit in the meantime. `RECOVERED`,
`ESCALATED`, and `EXHAUSTED` are terminal — every transition is checked
against an explicit allow-list, so an invalid jump (e.g. `DETECTED`
straight to `RECOVERED`) is rejected, not silently allowed.

#### Simulated execution (deterministic, never random)

- `retry_payment`: recovered if the customer's historical success rate
  is ≥ 50%, otherwise failed — same inputs always produce the same
  outcome.
- `schedule_retry` / `send_payment_reminder` / `request_payment_method_update`:
  deterministically land on `failed` with a descriptive
  `execution_status` (`scheduled`, `pending_customer_action`,
  `action_required`) — nothing to recover *yet*, by design; a later
  phase's webhook integration would resolve these for real.
- `escalate`: always lands on `escalated`.

`recovered_amount` is clamped so it can never exceed `amount_at_risk`.

#### Idempotency

Planning an already-planned case, validating an already-validated one,
or executing an already-terminal one all return the existing result
instead of redoing the work — no duplicate plans, no double-counted
revenue, safe to retry any step any number of times.

#### Audit trail

Every plan/validate/execute step appends a row to
`recovery_action_history` (action, previous/new state, reason,
validation result, execution result, amount, timestamp) — the full
decision history for a case is always reconstructable.

#### API usage

```bash
# Select and record an action for this opportunity
curl -X POST http://localhost:8000/api/recovery/opportunities/rec_pay_sub_004595/plan

# Run the safety validator (does not execute anything)
curl -X POST http://localhost:8000/api/recovery/opportunities/rec_pay_sub_004595/validate

# Simulate executing the validated action (local only, no real payment call)
curl -X POST http://localhost:8000/api/recovery/opportunities/rec_pay_sub_004595/execute

# Full plan/validate/execute history for a case
curl http://localhost:8000/api/recovery/opportunities/rec_pay_sub_004595/history

# Aggregate action metrics across every case
curl http://localhost:8000/api/recovery/action-summary
```

Example `execute` response:

```json
{
  "already_executed": false,
  "execution_status": "success",
  "recovered_amount": 2999.0,
  "status": "recovered",
  "failure_reason": null
}
```

#### Database migration

`recovery_cases` gained new nullable/defaulted columns (`action`,
`action_reason`, `planned_at`, `last_validation_result`,
`last_validation_reason`, `execution_status`, `executed_at`,
`execution_failure_reason`, `recovered_amount`, `recovery_attempts`),
and a new `recovery_action_history` table was added. Nothing is dropped
or rewritten — existing customer/subscription/payment/recovery-case data
is untouched. Run once, safe to re-run:

```bash
python -m app.db.migrate_phase4
```

### 7. AI intelligence layer (Ollama / Qwen 2.5 3B) — recommends, never decides

> **AI recommends. Deterministic safety logic validates. Recovery Engine executes.**

Phase 5 adds a local LLM (Qwen 2.5 3B via Ollama) that looks at a
recovery opportunity and *suggests* an action, purely as a second
opinion alongside Phase 4's deterministic engine. The AI can never plan,
validate, or execute a recovery action itself, and it never touches
Razorpay or any real payment — those remain exclusively Phase 4's job,
completely unmodified in what it's allowed to do.

```
Recovery Opportunity
        ↓
Controlled Context Builder        (app/ai/context.py)
        ↓
Local Ollama / Qwen 2.5 3B        (app/ai/ollama_provider.py)
        ↓
Structured AI Recommendation      (raw JSON text)
        ↓
Pydantic Validation                (app/ai/schemas.py -- rejects anything
        ↓                            that doesn't fit the bounded shape)
Deterministic Safety Validator    (the *same* app.recovery.action_rules
        ↓                            .validate_safety Phase 4 uses)
Fallback / Approval
        ↓
Existing Phase 4 Recovery Engine  (unchanged -- still the only thing
                                    that ever plans/validates/executes)
```

No cloud AI, no API keys, no LangChain/LangGraph/RAG/vector DB/agents —
just an HTTP call to a local Ollama server and a validated JSON contract.

#### Ollama / Qwen 2.5 3B setup

Install Ollama locally and pull the model (once):

```bash
ollama pull qwen2.5:3b
```

Environment variables (`backend/.env`, all optional -- these are the
defaults):

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=60
```

No API key -- Ollama is a local server. RecoverAI works fully without
Ollama running at all; see **Fallback behavior** below.

#### AI context (what the model sees)

A small, controlled dict built fresh per case -- never the whole
database, never PII (there isn't any to begin with: customers are
identified only by generated ids): payment amount/status/failure
reason, failure category, retry count, customer success rate and
successful/failed payment counts, customer lifetime value, subscription
status, recovery priority, amount at risk, prior recovery attempts, and
the Phase 3/4 deterministic action for reference.

#### Structured output

The model must return JSON only, matching one fixed shape:

```json
{
  "recommended_action": "RETRY_PAYMENT",
  "confidence": 0.82,
  "reason": "The customer has a strong payment history and the failure appears temporary.",
  "risk_level": "LOW",
  "customer_context": "Customer has successfully completed most previous payments.",
  "alternative_action": "SCHEDULE_RETRY"
}
```

`recommended_action` and `alternative_action` are restricted to the same
five actions Phase 4 already knows: `RETRY_PAYMENT`, `SCHEDULE_RETRY`,
`SEND_PAYMENT_REMINDER`, `REQUEST_PAYMENT_METHOD_UPDATE`, `ESCALATE` --
Pydantic rejects anything else, along with out-of-range confidence,
an invalid risk level, missing fields, or an empty/oversized reason.
Invalid output is never trusted; it's recorded as a failed AI call and
the system falls back to the deterministic action.

#### Safety architecture

The AI's suggested action is run through **the exact same**
`validate_safety` function Phase 4 uses for real planned actions (not a
separate, weaker copy) -- rejected if the payment already succeeded, the
case is already terminal, the retry limit is exhausted, the subscription
is canceled and the action would retry anyway, or the action isn't
valid for the case's failure category. A rejected AI recommendation is
never executed; the deterministic action is used instead.

#### AI vs. deterministic decision

Every AI call records both `deterministic_action` (what Phase 4's rules
say) and `ai_recommended_action` (what the model said), whether they
`agreement`d, the safety validation outcome, and whether `fallback_used`
is true. This is what lets AI recommendations be measured against the
deterministic baseline over time -- the AI is not asked to replace it.

#### Fallback behavior

If Ollama is unreachable, times out, returns something malformed, or its
JSON fails validation, that specific call is recorded with its failure
status (`unavailable`, `timeout`, `provider_error`, `invalid_json`,
`invalid_schema`) and `fallback_used=true` -- the deterministic Phase 4
action is always still available, and the rest of RecoverAI keeps
working normally. AI being down never breaks the app.

#### Database

New table only: `ai_recommendations` (one row per AI analysis run --
`ai_recommended_action`, `ai_confidence`, `ai_reason`, `ai_risk_level`,
`ai_customer_context`, `ai_alternative_action`, `ai_status`, `ai_model`,
`ai_generated_at`, `deterministic_action`, `safety_validation_result`,
`fallback_used`, `effective_action`). Nothing existing is altered.
Additive, safe to re-run:

```bash
python -m app.db.migrate_phase5
```

#### API usage

```bash
# Single opportunity: AI recommendation + deterministic comparison + safety check
curl -X POST http://localhost:8000/api/recovery/opportunities/rec_pay_sub_004595/ai-recommend

# Batch: analyzes the next N not-yet-analyzed opportunities (default 10, max 50)
curl -X POST "http://localhost:8000/api/recovery/ai/analyze?batch_size=10"

# Aggregate metrics
curl http://localhost:8000/api/recovery/ai-summary
```

`ai-summary` returns cases analyzed, successful/failed AI calls,
agreements/disagreements with the deterministic engine, rejected
recommendations, fallback count, average confidence, breakdowns by
action and risk level, and a live `ollama_available` check.

#### Testing

All Phase 5 automated tests mock the `AIProvider` interface (a
`FakeAIProvider` test double, plus `httpx.MockTransport` for the Ollama
HTTP layer itself) -- none of them require a running Ollama server.
They cover valid/invalid/malformed AI responses, every Pydantic
rejection case, provider timeout/unavailable/error handling, agreement
and disagreement with the deterministic engine, an unsafe AI
recommendation being rejected and falling back, escalation, context
construction (compact, no PII), database persistence, and all three API
endpoints (including empty-dataset and per-case-failure-in-a-batch
cases).

#### Live verification (run this yourself, against your own Ollama)

A live Ollama server isn't reachable from a sandboxed build/CI
environment, so live verification is a separate, deliberate step you run
locally once Ollama is installed and the backend is up:

```bash
cd backend
python scripts/verify_live_ollama.py --count 2
```

This checks Ollama is reachable, picks 1-3 *existing* recovery
opportunities from your local database (creates nothing), calls the real
`/ai-recommend` endpoint against your running backend for each, and
prints the full result -- AI recommendation, deterministic comparison,
safety validation, fallback status. It deliberately does not process the
full opportunity set (by design: no GPU, ~8GB RAM -- keep batches and
live tests small), and it never plans/validates/executes a recovery
action or moves any money.

### 8. Web dashboard (Phase 6)

A real UI on top of everything above — the frontend was a static
homepage through Phase 5; Phase 6 replaces it with a working dashboard
that only *consumes* the existing backend API. No new business logic
was added to the frontend, no bulk-execute endpoint was added to the
backend, and the plan → validate → execute sequence is unchanged: every
action button on the case detail page calls one existing per-case
endpoint, in order, exactly as before.

**Stack:** Next.js App Router + TypeScript + Tailwind (already
scaffolded in Phase 1) + `@tanstack/react-query` (data fetching/caching,
mutation state for the action buttons) + `recharts` (charts). No new
backend dependency, no new database table or column, no state
management library beyond React Query's cache.

**Pages:**

| Route | Purpose |
|---|---|
| `/` | Executive dashboard — KPI tiles (payments analyzed, opportunities, revenue at risk, simulated recovered revenue, Ollama status) sourced from `/api/data/summary`, `/api/recovery/summary`, `/api/recovery/action-summary`, `/api/recovery/ai-summary`; priority/outcome charts; **Run Detection** and **Run AI Batch (10)** buttons |
| `/opportunities` | Filterable, paginated table over `GET /api/recovery/opportunities` (priority/status/failure_category/min·max amount) |
| `/opportunities/[id]` | Case detail — payment/customer/detection context, the **Plan → Validate → Execute** buttons (each a direct call to the existing per-case endpoint), the **AI Recommendation** panel (deterministic vs. AI, agreement, safety validation, fallback), and the full audit-trail timeline from `GET .../history` |
| `/ai` | AI intelligence analytics from `/api/recovery/ai-summary` — agreement/disagreement, rejected recommendations, fallback count, average confidence, breakdowns by action and risk level, live Ollama availability |

A persistent banner — **"Simulated / Advisory Only — No real payments
are executed."** — is rendered in the root layout on every page.

**Safety model, unchanged:** the UI never skips validation, never
bulk-executes, and never lets the AI's suggestion bypass the safety
validator. `lib/api-client.ts` is a thin typed wrapper with one function
per existing endpoint — no recovery/eligibility/priority logic is
duplicated in the frontend; every decision still happens in the Python
backend exactly as in Phases 3-5.

**Testing:** Vitest + React Testing Library (`npm test`) covers the API
client (request shaping, query params, error handling — mocked
`fetch`, no backend needed), the formatters, and key components
(`AdvisoryBanner` always renders the required text; `ActionButton`
disables itself and shows a pending label while a mutation is in
flight; badges render every known status/priority/risk value). `npm run
build` and `npm run lint` both pass clean.

**Manual verification:** driven end-to-end with a headless browser
against the real backend + Postgres dataset — dashboard KPIs and charts
render real numbers; opportunity filters narrow the table correctly;
a case's Plan → Validate → Execute buttons were clicked in sequence and
correctly replayed the FAILED → PLANNED → VALIDATED → EXECUTING → FAILED
retry loop with a new audit-trail entry per step; the AI Recommendation
button was clicked with Ollama genuinely offline and rendered the exact
fallback message with the real connection-refused error and the
deterministic effective action; the AI Analytics page correctly showed
"Ollama: Unavailable" and empty-but-not-broken charts.

**Deployment (Vercel + Render) — not yet actually deployed, config
only:** the frontend is a standard Next.js app (`NEXT_PUBLIC_API_BASE_URL`
pointed at the Render backend); the backend needs `CORS_ORIGINS` to
include the Vercel domain and a managed Postgres add-on. Ollama isn't
practical to run on a typical Render web service — a deployed instance
would show "Ollama: Unavailable" and fall back to deterministic actions
throughout, which is itself a legitimate demonstration of the fallback
behavior Phase 5 was built for, not a bug.

## Status

**Phase 1:** project scaffolding — backend/frontend skeletons, health
check API, homepage, and local Postgres configuration.

**Phase 2:** database models and a synthetic payment/revenue dataset
(customers, subscriptions, payments), plus a duplicate-safe seeding
script and a `/api/data/summary` endpoint to verify the data.

**Phase 3:** a deterministic revenue leakage detection engine that
analyzes payments and creates prioritized `RecoveryCase` records
(rule-based eligibility, HIGH/MEDIUM/LOW priority, no ML/LLM), plus
`/api/recovery/detect`, `/opportunities`, `/opportunities/{id}`, and
`/summary` endpoints.

**Phase 4:** a deterministic recovery action engine (action selection,
safety validation, a state machine, simulated -- not real -- execution)
with a full audit trail, driving each `RecoveryCase` through plan →
validate → execute via `/opportunities/{id}/plan`, `/validate`,
`/execute`, `/history`, and `/action-summary`.

**Phase 5:** a local AI intelligence layer (Ollama + Qwen 2.5 3B) that
produces advisory recommendations alongside the deterministic engine --
structured, Pydantic-validated, safety-gated through Phase 4's own
validator, and always falling back to the deterministic action if the
AI is unavailable or its output is rejected.

**Phase 6 (current):** a Next.js web dashboard (executive summary,
opportunities table, case detail with the Plan → Validate → Execute
controls and AI recommendation panel, AI analytics, full audit-trail
timeline) that consumes the existing backend API as-is -- no new
business logic in the frontend, no bulk-execute endpoint, safety model
unchanged. A persistent "Simulated / Advisory Only" banner is shown on
every page.

No real payment has been recovered by any phase so far, Razorpay is not
yet integrated, and the app has not been deployed to Vercel/Render (see
§8) -- only local verification has been performed.

Not implemented yet: Razorpay integration and webhooks, real payment
execution, authentication, and an actual Vercel/Render deployment.
