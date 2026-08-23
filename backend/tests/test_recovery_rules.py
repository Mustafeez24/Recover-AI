from datetime import date, datetime

from app.models import (
    Customer,
    FailureCategory,
    FailureReason,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RecoveryPriority,
    Subscription,
    SubscriptionStatus,
)
from app.recovery.rules import (
    analyze_payment,
    calculate_priority,
    classify_failure_category,
    customer_success_rate,
    evaluate_eligibility,
)


def make_customer(success=5, failed=5, lifetime_value=1000.0):
    return Customer(
        customer_id="cus_test",
        customer_since=date(2024, 1, 1),
        total_successful_payments=success,
        total_failed_payments=failed,
        lifetime_value=lifetime_value,
        created_at=datetime.utcnow(),
    )


def make_payment(
    status=PaymentStatus.FAILED,
    failure_reason=FailureReason.TEMPORARY_FAILURE,
    amount=500.0,
    retry_count=0,
    subscription_id=None,
):
    return Payment(
        payment_id="pay_test",
        customer_id="cus_test",
        subscription_id=subscription_id,
        amount=amount,
        currency="INR",
        payment_status=status,
        failure_reason=failure_reason,
        payment_method=PaymentMethod.CARD,
        created_at=datetime(2024, 1, 1),
        retry_count=retry_count,
    )


def make_subscription(status=SubscriptionStatus.ACTIVE):
    return Subscription(
        subscription_id="sub_test",
        customer_id="cus_test",
        plan="standard",
        amount=599.0,
        status=status,
        next_payment_date=None,
        created_at=datetime(2024, 1, 1),
    )


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def test_successful_payment_is_not_recoverable():
    payment = make_payment(status=PaymentStatus.SUCCESS, failure_reason=None)
    eligible, reason = evaluate_eligibility(payment, None)
    assert eligible is False
    assert "already succeeded" in reason


def test_eligible_temporary_failure():
    payment = make_payment(failure_reason=FailureReason.TEMPORARY_FAILURE, retry_count=1)
    eligible, _ = evaluate_eligibility(payment, None)
    assert eligible is True
    assert classify_failure_category(payment) == FailureCategory.TEMPORARY_FAILURE


def test_eligible_insufficient_funds_failure():
    payment = make_payment(failure_reason=FailureReason.INSUFFICIENT_FUNDS, retry_count=0)
    eligible, _ = evaluate_eligibility(payment, None)
    assert eligible is True
    assert classify_failure_category(payment) == FailureCategory.INSUFFICIENT_FUNDS


def test_eligible_timeout():
    payment = make_payment(status=PaymentStatus.TIMEOUT, failure_reason=FailureReason.TIMEOUT)
    eligible, _ = evaluate_eligibility(payment, None)
    assert eligible is True
    assert classify_failure_category(payment) == FailureCategory.PAYMENT_TIMEOUT


def test_eligible_abandoned_checkout():
    payment = make_payment(status=PaymentStatus.ABANDONED, failure_reason=FailureReason.CHECKOUT_ABANDONED)
    eligible, _ = evaluate_eligibility(payment, None)
    assert eligible is True
    assert classify_failure_category(payment) == FailureCategory.ABANDONED_CHECKOUT


def test_eligible_repeated_failure():
    payment = make_payment(failure_reason=FailureReason.BANK_DECLINED, retry_count=2)
    eligible, _ = evaluate_eligibility(payment, None)
    assert eligible is True
    assert classify_failure_category(payment) == FailureCategory.REPEATED_FAILURE


def test_eligible_subscription_payment_failure():
    payment = make_payment(
        failure_reason=FailureReason.BANK_DECLINED, retry_count=0, subscription_id="sub_test"
    )
    subscription = make_subscription(status=SubscriptionStatus.PAST_DUE)
    eligible, _ = evaluate_eligibility(payment, subscription)
    assert eligible is True
    assert classify_failure_category(payment) == FailureCategory.SUBSCRIPTION_FAILURE


def test_excessive_retry_count_is_not_eligible():
    payment = make_payment(failure_reason=FailureReason.TEMPORARY_FAILURE, retry_count=4)
    eligible, reason = evaluate_eligibility(payment, None)
    assert eligible is False
    assert "exhausted" in reason


def test_canceled_subscription_is_not_eligible():
    payment = make_payment(
        failure_reason=FailureReason.BANK_DECLINED, retry_count=1, subscription_id="sub_test"
    )
    subscription = make_subscription(status=SubscriptionStatus.CANCELED)
    eligible, reason = evaluate_eligibility(payment, subscription)
    assert eligible is False
    assert "canceled" in reason


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------


def test_high_value_payment_priority():
    payment = make_payment(amount=3000.0, retry_count=0)
    customer = make_customer(success=9, failed=1)  # 90% success rate
    priority, _ = calculate_priority(payment, customer, FailureCategory.TEMPORARY_FAILURE)
    assert priority == RecoveryPriority.HIGH


def test_low_value_payment_priority():
    payment = make_payment(amount=100.0, retry_count=3)
    customer = make_customer(success=1, failed=9)  # 10% success rate
    priority, _ = calculate_priority(payment, customer, FailureCategory.TEMPORARY_FAILURE)
    assert priority == RecoveryPriority.LOW


def test_customer_with_strong_history_scores_higher():
    payment = make_payment(amount=800.0, retry_count=1)
    strong_customer = make_customer(success=9, failed=1)
    weak_customer = make_customer(success=1, failed=9)

    strong_priority, _ = calculate_priority(payment, strong_customer, FailureCategory.TEMPORARY_FAILURE)
    weak_priority, _ = calculate_priority(payment, weak_customer, FailureCategory.TEMPORARY_FAILURE)

    priority_rank = {RecoveryPriority.LOW: 0, RecoveryPriority.MEDIUM: 1, RecoveryPriority.HIGH: 2}
    assert priority_rank[strong_priority] > priority_rank[weak_priority]


def test_customer_success_rate_with_no_history_is_neutral():
    customer = make_customer(success=0, failed=0)
    assert customer_success_rate(customer) == 0.5


# ---------------------------------------------------------------------------
# analyze_payment (end-to-end rule composition)
# ---------------------------------------------------------------------------


def test_analyze_payment_success_not_recoverable():
    payment = make_payment(status=PaymentStatus.SUCCESS, failure_reason=None)
    customer = make_customer()
    result = analyze_payment(payment, customer, None)
    assert result["eligible"] is False
    assert result["priority"] is None
    assert result["amount_at_risk"] is None
    assert result["failure_category"] is None


def test_analyze_payment_amount_at_risk_matches_payment_amount():
    payment = make_payment(amount=4999.0, retry_count=0)
    customer = make_customer(success=8, failed=2)
    result = analyze_payment(payment, customer, None)
    assert result["eligible"] is True
    assert result["amount_at_risk"] == 4999.0


def test_analyze_payment_includes_reason_and_next_step():
    payment = make_payment(status=PaymentStatus.ABANDONED, failure_reason=FailureReason.CHECKOUT_ABANDONED)
    customer = make_customer()
    result = analyze_payment(payment, customer, None)
    assert result["eligible"] is True
    assert result["detection_reason"]
    assert result["recommended_next_step"] == "send_checkout_reminder"
    assert result["customer_value"] == customer.lifetime_value
