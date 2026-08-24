"""Deterministic synthetic payment/revenue dataset generator.

Generates fictional customers, subscriptions, and payments covering the
success/failure scenarios Phase 3+ will need (insufficient funds, temporary
failures, timeouts, repeated retries, subscription payment failures, and
abandoned checkouts). No real personal or payment data is used anywhere:
customers are identified only by a generated id, with no names, emails, or
other PII fields.

Generation is deterministic: the same `seed` always produces the exact same
rows (same ids, same field values), which is what makes the seeding script
safe to re-run without creating duplicate data.
"""

import random
from datetime import date, datetime, timedelta

import pandas as pd

from app.models.enums import FailureReason, PaymentMethod, PaymentStatus, SubscriptionStatus

SEED = 42
NUM_CUSTOMERS = 1200
SUBSCRIPTION_RATE = 0.35
TARGET_PAYMENTS = 5200
CURRENCY = "INR"

PLANS = [
    ("basic", 299.00),
    ("standard", 599.00),
    ("pro", 1299.00),
    ("enterprise", 2999.00),
]

ONE_OFF_AMOUNTS = [199.00, 499.00, 999.00, 1499.00, 2499.00]

PAYMENT_METHODS = list(PaymentMethod)

# One-off / checkout payments can be abandoned before a method is even picked.
CHECKOUT_OUTCOME_WEIGHTS = [
    (PaymentStatus.SUCCESS, 0.78),
    (PaymentStatus.FAILED, 0.13),
    (PaymentStatus.TIMEOUT, 0.04),
    (PaymentStatus.ABANDONED, 0.05),
]

# Subscription renewals are auto-charged, so "abandoned" doesn't apply.
SUBSCRIPTION_OUTCOME_WEIGHTS = [
    (PaymentStatus.SUCCESS, 0.80),
    (PaymentStatus.FAILED, 0.14),
    (PaymentStatus.TIMEOUT, 0.06),
]

FAILURE_REASON_WEIGHTS = [
    (FailureReason.INSUFFICIENT_FUNDS, 0.40),
    (FailureReason.TEMPORARY_FAILURE, 0.25),
    (FailureReason.BANK_DECLINED, 0.20),
    (FailureReason.NETWORK_ERROR, 0.15),
]


def _weighted_choice(rng: random.Random, weighted):
    items, weights = zip(*weighted)
    return rng.choices(items, weights=weights, k=1)[0]


def _make_retry_count(rng: random.Random, status: PaymentStatus) -> int:
    if status == PaymentStatus.SUCCESS:
        return rng.choices([0, 1], weights=[0.85, 0.15])[0]
    if status == PaymentStatus.FAILED:
        # Higher counts here represent the "repeated payment failures" scenario.
        return rng.choices([0, 1, 2, 3, 4], weights=[0.25, 0.30, 0.25, 0.13, 0.07])[0]
    if status == PaymentStatus.TIMEOUT:
        return rng.choices([0, 1], weights=[0.7, 0.3])[0]
    return 0  # abandoned: no retry ever attempted


def _make_failure_reason(rng: random.Random, status: PaymentStatus):
    if status == PaymentStatus.SUCCESS:
        return None
    if status == PaymentStatus.TIMEOUT:
        return FailureReason.TIMEOUT
    if status == PaymentStatus.ABANDONED:
        return FailureReason.CHECKOUT_ABANDONED
    return _weighted_choice(rng, FAILURE_REASON_WEIGHTS)


def generate_customers(rng: random.Random, n: int = NUM_CUSTOMERS, today: date = None):
    today = today or date.today()
    customers = []
    for i in range(1, n + 1):
        days_since = rng.randint(30, 900)
        customers.append(
            {
                "customer_id": f"cus_{i:05d}",
                "customer_since": today - timedelta(days=days_since),
                "total_successful_payments": 0,
                "total_failed_payments": 0,
                "lifetime_value": 0.0,
                "created_at": datetime.utcnow(),
            }
        )
    return customers


def generate_subscriptions(rng: random.Random, customers: list, today: date = None):
    today = today or date.today()
    subscriptions = []
    subscribed_ids = set()
    counter = 1
    for c in customers:
        if rng.random() < SUBSCRIPTION_RATE:
            plan, amount = rng.choice(PLANS)
            sub_id = f"sub_{counter:05d}"
            counter += 1
            subscriptions.append(
                {
                    "subscription_id": sub_id,
                    "customer_id": c["customer_id"],
                    "plan": plan,
                    "amount": amount,
                    "status": SubscriptionStatus.ACTIVE,  # refined after payments are generated
                    "next_payment_date": None,
                    "created_at": datetime.combine(c["customer_since"], datetime.min.time()),
                }
            )
            subscribed_ids.add(c["customer_id"])
    return subscriptions, subscribed_ids


def generate_subscription_payments(rng: random.Random, subscriptions: list, today: date = None):
    today = today or date.today()
    payments = []
    counter = 1
    sub_updates = {}

    for sub in subscriptions:
        start = sub["created_at"].date()
        cycles = max(1, min((today - start).days // 30 + 1, 14))
        last_status = None
        last_date = None
        consecutive_failures = 0

        for i in range(cycles):
            cycle_date = start + timedelta(days=30 * i)
            if cycle_date > today:
                break

            status = _weighted_choice(rng, SUBSCRIPTION_OUTCOME_WEIGHTS)
            retry_count = _make_retry_count(rng, status)
            failure_reason = _make_failure_reason(rng, status)
            created_at = datetime.combine(cycle_date, datetime.min.time()) + timedelta(
                hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
            )

            payments.append(
                {
                    "payment_id": f"pay_sub_{counter:06d}",
                    "customer_id": sub["customer_id"],
                    "subscription_id": sub["subscription_id"],
                    "amount": sub["amount"],
                    "currency": CURRENCY,
                    "payment_status": status,
                    "failure_reason": failure_reason,
                    "payment_method": rng.choice(PAYMENT_METHODS),
                    "created_at": created_at,
                    "retry_count": retry_count,
                }
            )
            counter += 1

            last_status = status
            last_date = cycle_date
            if status in (PaymentStatus.FAILED, PaymentStatus.TIMEOUT):
                consecutive_failures += 1
            else:
                consecutive_failures = 0

        if last_status == PaymentStatus.SUCCESS:
            sub_status = SubscriptionStatus.ACTIVE
            next_payment_date = last_date + timedelta(days=30)
        elif consecutive_failures >= 3:
            sub_status = SubscriptionStatus.CANCELED
            next_payment_date = None
        elif last_status in (PaymentStatus.FAILED, PaymentStatus.TIMEOUT):
            sub_status = SubscriptionStatus.PAST_DUE
            next_payment_date = last_date + timedelta(days=3)
        else:
            sub_status = SubscriptionStatus.ACTIVE
            next_payment_date = today + timedelta(days=30)

        sub_updates[sub["subscription_id"]] = (sub_status, next_payment_date)

    return payments, sub_updates


def generate_one_off_payments(
    rng: random.Random,
    customers: list,
    subscribed_ids: set,
    counter_start: int = 1,
    today: date = None,
):
    today = today or date.today()
    payments = []
    counter = counter_start

    for c in customers:
        if c["customer_id"] in subscribed_ids:
            continue
        n_payments = rng.randint(1, 6)
        max_days_ago = min(900, (today - c["customer_since"]).days)
        for _ in range(n_payments):
            days_ago = rng.randint(0, max(0, max_days_ago))
            pay_date = today - timedelta(days=days_ago)
            status = _weighted_choice(rng, CHECKOUT_OUTCOME_WEIGHTS)
            retry_count = _make_retry_count(rng, status)
            failure_reason = _make_failure_reason(rng, status)
            payment_method = None if status == PaymentStatus.ABANDONED else rng.choice(PAYMENT_METHODS)
            created_at = datetime.combine(pay_date, datetime.min.time()) + timedelta(
                hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
            )

            payments.append(
                {
                    "payment_id": f"pay_one_{counter:06d}",
                    "customer_id": c["customer_id"],
                    "subscription_id": None,
                    "amount": rng.choice(ONE_OFF_AMOUNTS),
                    "currency": CURRENCY,
                    "payment_status": status,
                    "failure_reason": failure_reason,
                    "payment_method": payment_method,
                    "created_at": created_at,
                    "retry_count": retry_count,
                }
            )
            counter += 1

    return payments, counter


def _pad_payments(rng: random.Random, customers: list, counter_start: int, needed: int, today: date = None):
    """Top up the dataset with extra one-off payments if still short of the target."""
    today = today or date.today()
    payments = []
    counter = counter_start
    for _ in range(needed):
        c = rng.choice(customers)
        status = _weighted_choice(rng, CHECKOUT_OUTCOME_WEIGHTS)
        retry_count = _make_retry_count(rng, status)
        failure_reason = _make_failure_reason(rng, status)
        payment_method = None if status == PaymentStatus.ABANDONED else rng.choice(PAYMENT_METHODS)
        days_ago = rng.randint(0, 365)
        created_at = datetime.combine(today - timedelta(days=days_ago), datetime.min.time())

        payments.append(
            {
                "payment_id": f"pay_pad_{counter:06d}",
                "customer_id": c["customer_id"],
                "subscription_id": None,
                "amount": rng.choice(ONE_OFF_AMOUNTS),
                "currency": CURRENCY,
                "payment_status": status,
                "failure_reason": failure_reason,
                "payment_method": payment_method,
                "created_at": created_at,
                "retry_count": retry_count,
            }
        )
        counter += 1
    return payments


def _apply_customer_aggregates(customers: list, payments: list):
    stats = {c["customer_id"]: {"success": 0, "failed": 0, "value": 0.0} for c in customers}
    for p in payments:
        s = stats[p["customer_id"]]
        if p["payment_status"] == PaymentStatus.SUCCESS:
            s["success"] += 1
            s["value"] += p["amount"]
        elif p["payment_status"] in (PaymentStatus.FAILED, PaymentStatus.TIMEOUT):
            s["failed"] += 1

    for c in customers:
        s = stats[c["customer_id"]]
        c["total_successful_payments"] = s["success"]
        c["total_failed_payments"] = s["failed"]
        c["lifetime_value"] = round(s["value"], 2)


def _apply_subscription_updates(subscriptions: list, sub_updates: dict):
    for sub in subscriptions:
        status, next_payment_date = sub_updates[sub["subscription_id"]]
        sub["status"] = status
        sub["next_payment_date"] = next_payment_date


def generate_dataset(seed: int = SEED, target_payments: int = TARGET_PAYMENTS, today: date = None):
    """Generate the full synthetic dataset deterministically.

    Returns (customers, subscriptions, payments) as lists of plain dicts
    matching the corresponding SQLAlchemy model columns.
    """
    today = today or date.today()
    rng = random.Random(seed)

    customers = generate_customers(rng, today=today)
    subscriptions, subscribed_ids = generate_subscriptions(rng, customers, today=today)

    sub_payments, sub_updates = generate_subscription_payments(rng, subscriptions, today=today)
    one_off_payments, next_counter = generate_one_off_payments(
        rng, customers, subscribed_ids, counter_start=1, today=today
    )

    payments = sub_payments + one_off_payments

    if len(payments) < target_payments:
        extra = _pad_payments(rng, customers, next_counter, target_payments - len(payments), today=today)
        payments.extend(extra)

    _apply_subscription_updates(subscriptions, sub_updates)
    _apply_customer_aggregates(customers, payments)

    return customers, subscriptions, payments


def generate_dataframes(seed: int = SEED, target_payments: int = TARGET_PAYMENTS, today: date = None):
    """Same as generate_dataset(), returned as pandas DataFrames."""
    customers, subscriptions, payments = generate_dataset(seed, target_payments, today)
    return pd.DataFrame(customers), pd.DataFrame(subscriptions), pd.DataFrame(payments)
