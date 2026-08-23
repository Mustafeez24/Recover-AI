from datetime import date, datetime

from app.models import (
    Customer,
    FailureReason,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RecoveryCase,
)
from app.recovery.engine import get_summary, run_detection


def _add_customer(db, customer_id="cus_001", success=5, failed=2, lifetime_value=2000.0):
    c = Customer(
        customer_id=customer_id,
        customer_since=date(2024, 1, 1),
        total_successful_payments=success,
        total_failed_payments=failed,
        lifetime_value=lifetime_value,
        created_at=datetime.utcnow(),
    )
    db.add(c)
    db.commit()
    return c


def _add_payment(db, payment_id, customer_id, status, failure_reason=None, amount=500.0, retry_count=0):
    p = Payment(
        payment_id=payment_id,
        customer_id=customer_id,
        subscription_id=None,
        amount=amount,
        currency="INR",
        payment_status=status,
        failure_reason=failure_reason,
        payment_method=PaymentMethod.CARD,
        created_at=datetime(2024, 1, 1),
        retry_count=retry_count,
    )
    db.add(p)
    db.commit()
    return p


def test_empty_dataset_runs_without_error(db_session):
    result = run_detection(db_session)
    assert result == {
        "payments_scanned": 0,
        "failed_payments_scanned": 0,
        "opportunities_created": 0,
        "duplicates_skipped": 0,
        "ineligible_skipped": 0,
    }
    summary = get_summary(db_session)
    assert summary["total_payments_analyzed"] == 0
    assert summary["recovery_opportunities"] == 0
    assert summary["total_revenue_at_risk"] == 0


def test_detection_creates_recovery_case_for_eligible_payment(db_session):
    _add_customer(db_session)
    _add_payment(
        db_session,
        "pay_001",
        "cus_001",
        PaymentStatus.FAILED,
        FailureReason.TEMPORARY_FAILURE,
        amount=1500.0,
        retry_count=1,
    )

    result = run_detection(db_session)
    assert result["payments_scanned"] == 1
    assert result["failed_payments_scanned"] == 1
    assert result["opportunities_created"] == 1

    case = db_session.get(RecoveryCase, "rec_pay_001")
    assert case is not None
    assert case.payment_id == "pay_001"
    assert float(case.amount_at_risk) == 1500.0


def test_detection_skips_successful_payments(db_session):
    _add_customer(db_session)
    _add_payment(db_session, "pay_002", "cus_001", PaymentStatus.SUCCESS)

    result = run_detection(db_session)
    assert result["opportunities_created"] == 0
    assert db_session.query(RecoveryCase).count() == 0


def test_detection_is_idempotent_no_duplicates(db_session):
    _add_customer(db_session)
    _add_payment(
        db_session, "pay_003", "cus_001", PaymentStatus.FAILED, FailureReason.INSUFFICIENT_FUNDS, retry_count=0
    )

    first = run_detection(db_session)
    assert first["opportunities_created"] == 1

    second = run_detection(db_session)
    assert second["opportunities_created"] == 0
    assert second["duplicates_skipped"] == 1

    assert db_session.query(RecoveryCase).count() == 1


def test_detection_running_three_times_is_still_safe(db_session):
    _add_customer(db_session)
    _add_payment(db_session, "pay_004", "cus_001", PaymentStatus.TIMEOUT, FailureReason.TIMEOUT)

    run_detection(db_session)
    run_detection(db_session)
    run_detection(db_session)

    assert db_session.query(RecoveryCase).count() == 1


def test_excessive_retry_does_not_create_case(db_session):
    _add_customer(db_session)
    _add_payment(
        db_session,
        "pay_005",
        "cus_001",
        PaymentStatus.FAILED,
        FailureReason.BANK_DECLINED,
        retry_count=4,
    )

    result = run_detection(db_session)
    assert result["opportunities_created"] == 0
    assert result["ineligible_skipped"] == 1
    assert db_session.query(RecoveryCase).count() == 0


def test_summary_matches_created_opportunities(db_session):
    _add_customer(db_session, customer_id="cus_a", lifetime_value=1000.0)
    _add_customer(db_session, customer_id="cus_b", lifetime_value=5000.0)

    _add_payment(db_session, "pay_a1", "cus_a", PaymentStatus.FAILED, FailureReason.TEMPORARY_FAILURE, amount=300.0)
    _add_payment(db_session, "pay_b1", "cus_b", PaymentStatus.FAILED, FailureReason.INSUFFICIENT_FUNDS, amount=2500.0)
    _add_payment(db_session, "pay_a2", "cus_a", PaymentStatus.SUCCESS, amount=100.0)

    run_detection(db_session)
    summary = get_summary(db_session)

    assert summary["total_payments_analyzed"] == 3
    assert summary["failed_payments_analyzed"] == 2
    assert summary["recovery_opportunities"] == 2
    assert summary["total_revenue_at_risk"] == 2800.0
    assert summary["non_recoverable_payments"] == 0
    assert (
        summary["high_priority_opportunities"]
        + summary["medium_priority_opportunities"]
        + summary["low_priority_opportunities"]
        == 2
    )
