from datetime import date

from app.data_generation.generator import generate_dataset
from app.data_generation.seed import _insert_new
from app.models import Customer, FailureReason, Payment, PaymentStatus, Subscription

TODAY = date(2026, 1, 1)

REQUIRED_PAYMENT_FIELDS = {
    "payment_id",
    "customer_id",
    "subscription_id",
    "amount",
    "currency",
    "payment_status",
    "failure_reason",
    "payment_method",
    "created_at",
    "retry_count",
}

REQUIRED_CUSTOMER_FIELDS = {
    "customer_id",
    "customer_since",
    "total_successful_payments",
    "total_failed_payments",
    "lifetime_value",
}

REQUIRED_SUBSCRIPTION_FIELDS = {
    "subscription_id",
    "customer_id",
    "plan",
    "amount",
    "status",
    "next_payment_date",
}


def _generate(seed=42, target_payments=5200):
    return generate_dataset(seed=seed, target_payments=target_payments, today=TODAY)


def test_generates_at_least_5000_payments():
    _, _, payments = _generate()
    assert len(payments) >= 5000


def test_generation_is_deterministic():
    customers_a, subs_a, payments_a = _generate()
    customers_b, subs_b, payments_b = _generate()

    assert [c["customer_id"] for c in customers_a] == [c["customer_id"] for c in customers_b]
    assert [s["subscription_id"] for s in subs_a] == [s["subscription_id"] for s in subs_b]
    assert [p["payment_id"] for p in payments_a] == [p["payment_id"] for p in payments_b]
    assert [p["payment_status"] for p in payments_a] == [p["payment_status"] for p in payments_b]


def test_customer_records_have_required_fields():
    customers, _, _ = _generate()
    assert len(customers) > 0
    for c in customers:
        assert REQUIRED_CUSTOMER_FIELDS.issubset(c.keys())


def test_subscription_records_have_required_fields():
    _, subscriptions, _ = _generate()
    assert len(subscriptions) > 0
    for s in subscriptions:
        assert REQUIRED_SUBSCRIPTION_FIELDS.issubset(s.keys())


def test_payment_records_have_required_fields():
    _, _, payments = _generate()
    for p in payments:
        assert REQUIRED_PAYMENT_FIELDS.issubset(p.keys())


def test_all_payment_statuses_are_valid():
    _, _, payments = _generate()
    valid_statuses = set(PaymentStatus)
    for p in payments:
        assert p["payment_status"] in valid_statuses


def test_successful_payments_have_no_failure_reason():
    _, _, payments = _generate()
    for p in payments:
        if p["payment_status"] == PaymentStatus.SUCCESS:
            assert p["failure_reason"] is None


def test_scenario_successful_payments_present():
    _, _, payments = _generate()
    assert any(p["payment_status"] == PaymentStatus.SUCCESS for p in payments)


def test_scenario_insufficient_funds_present():
    _, _, payments = _generate()
    assert any(p["failure_reason"] == FailureReason.INSUFFICIENT_FUNDS for p in payments)


def test_scenario_temporary_failure_present():
    _, _, payments = _generate()
    assert any(p["failure_reason"] == FailureReason.TEMPORARY_FAILURE for p in payments)


def test_scenario_payment_timeout_present():
    _, _, payments = _generate()
    assert any(p["payment_status"] == PaymentStatus.TIMEOUT for p in payments)


def test_scenario_repeated_payment_failures_present():
    _, _, payments = _generate()
    assert any(p["payment_status"] == PaymentStatus.FAILED and p["retry_count"] > 1 for p in payments)


def test_scenario_subscription_payment_failures_present():
    _, _, payments = _generate()
    assert any(
        p["subscription_id"] is not None and p["payment_status"] in (PaymentStatus.FAILED, PaymentStatus.TIMEOUT)
        for p in payments
    )


def test_scenario_abandoned_checkout_present():
    _, _, payments = _generate()
    assert any(p["payment_status"] == PaymentStatus.ABANDONED for p in payments)


def test_customer_aggregates_match_payments():
    customers, _, payments = _generate()
    by_customer = {c["customer_id"]: c for c in customers}

    successes = {}
    failures = {}
    for p in payments:
        cid = p["customer_id"]
        if p["payment_status"] == PaymentStatus.SUCCESS:
            successes[cid] = successes.get(cid, 0) + 1
        elif p["payment_status"] in (PaymentStatus.FAILED, PaymentStatus.TIMEOUT):
            failures[cid] = failures.get(cid, 0) + 1

    sample_ids = list(by_customer.keys())[:20]
    for cid in sample_ids:
        c = by_customer[cid]
        assert c["total_successful_payments"] == successes.get(cid, 0)
        assert c["total_failed_payments"] == failures.get(cid, 0)


def test_database_insertion(db_session):
    customers, subscriptions, payments = _generate(target_payments=200)
    # Keep the test fast: only insert customers referenced by a small payment slice.
    payments = payments[:200]
    used_customer_ids = {p["customer_id"] for p in payments}
    customers = [c for c in customers if c["customer_id"] in used_customer_ids]
    used_sub_ids = {p["subscription_id"] for p in payments if p["subscription_id"]}
    subscriptions = [s for s in subscriptions if s["subscription_id"] in used_sub_ids]

    _insert_new(db_session, Customer, customers, "customer_id")
    db_session.commit()
    _insert_new(db_session, Subscription, subscriptions, "subscription_id")
    db_session.commit()
    _insert_new(db_session, Payment, payments, "payment_id")
    db_session.commit()

    assert db_session.query(Customer).count() == len(customers)
    assert db_session.query(Payment).count() == len(payments)


def test_duplicate_safe_seeding(db_session):
    customers, subscriptions, payments = _generate(target_payments=200)
    payments = payments[:200]
    used_customer_ids = {p["customer_id"] for p in payments}
    customers = [c for c in customers if c["customer_id"] in used_customer_ids]
    used_sub_ids = {p["subscription_id"] for p in payments if p["subscription_id"]}
    subscriptions = [s for s in subscriptions if s["subscription_id"] in used_sub_ids]

    first_customers = _insert_new(db_session, Customer, customers, "customer_id")
    db_session.commit()
    first_subs = _insert_new(db_session, Subscription, subscriptions, "subscription_id")
    db_session.commit()
    first_payments = _insert_new(db_session, Payment, payments, "payment_id")
    db_session.commit()

    assert first_customers == len(customers)
    assert first_subs == len(subscriptions)
    assert first_payments == len(payments)

    # Re-run with the identical, deterministically-generated rows: nothing new should insert.
    second_customers = _insert_new(db_session, Customer, customers, "customer_id")
    db_session.commit()
    second_subs = _insert_new(db_session, Subscription, subscriptions, "subscription_id")
    db_session.commit()
    second_payments = _insert_new(db_session, Payment, payments, "payment_id")
    db_session.commit()

    assert second_customers == 0
    assert second_subs == 0
    assert second_payments == 0
    assert db_session.query(Customer).count() == len(customers)
    assert db_session.query(Payment).count() == len(payments)
