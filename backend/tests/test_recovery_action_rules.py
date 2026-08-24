from datetime import date, datetime

from app.models import (
    Customer,
    FailureCategory,
    FailureReason,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RecoveryAction,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryPriority,
    Subscription,
    SubscriptionStatus,
)
from app.recovery.action_rules import (
    HIGH_RISK_ESCALATION_AMOUNT,
    RECOVERY_ATTEMPT_CAP,
    select_action,
    simulate_execution,
    validate_safety,
)
from app.recovery.rules import MAX_RETRY_CAP


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


def make_case(
    failure_category=FailureCategory.TEMPORARY_FAILURE,
    priority=RecoveryPriority.MEDIUM,
    amount_at_risk=500.0,
    status=RecoveryCaseStatus.PLANNED,
    action=None,
    recovery_attempts=0,
):
    return RecoveryCase(
        recovery_case_id="rec_pay_test",
        payment_id="pay_test",
        customer_id="cus_test",
        status=status.value,
        priority=priority,
        amount_at_risk=amount_at_risk,
        customer_value=1000.0,
        failure_category=failure_category,
        detection_reason="test",
        recommended_next_step="test",
        action=action.value if action else None,
        recovery_attempts=recovery_attempts,
    )


# ---------------------------------------------------------------------------
# Action selection: one scenario per failure category
# ---------------------------------------------------------------------------


def test_select_action_temporary_failure():
    case = make_case(failure_category=FailureCategory.TEMPORARY_FAILURE)
    payment = make_payment(retry_count=1)
    action, reason = select_action(case, payment, make_customer(), None)
    assert action == RecoveryAction.RETRY_PAYMENT
    assert reason


def test_select_action_timeout_first_attempt():
    case = make_case(failure_category=FailureCategory.PAYMENT_TIMEOUT)
    payment = make_payment(status=PaymentStatus.TIMEOUT, failure_reason=FailureReason.TIMEOUT, retry_count=0)
    action, _ = select_action(case, payment, make_customer(), None)
    assert action == RecoveryAction.RETRY_PAYMENT


def test_select_action_timeout_after_retry():
    case = make_case(failure_category=FailureCategory.PAYMENT_TIMEOUT)
    payment = make_payment(status=PaymentStatus.TIMEOUT, failure_reason=FailureReason.TIMEOUT, retry_count=1)
    action, _ = select_action(case, payment, make_customer(), None)
    assert action == RecoveryAction.SCHEDULE_RETRY


def test_select_action_insufficient_funds_high_priority():
    case = make_case(failure_category=FailureCategory.INSUFFICIENT_FUNDS, priority=RecoveryPriority.HIGH)
    payment = make_payment(failure_reason=FailureReason.INSUFFICIENT_FUNDS)
    action, _ = select_action(case, payment, make_customer(), None)
    assert action == RecoveryAction.SCHEDULE_RETRY


def test_select_action_insufficient_funds_low_priority():
    case = make_case(failure_category=FailureCategory.INSUFFICIENT_FUNDS, priority=RecoveryPriority.LOW)
    payment = make_payment(failure_reason=FailureReason.INSUFFICIENT_FUNDS)
    action, _ = select_action(case, payment, make_customer(), None)
    assert action == RecoveryAction.SEND_PAYMENT_REMINDER


def test_select_action_abandoned_checkout():
    case = make_case(failure_category=FailureCategory.ABANDONED_CHECKOUT)
    payment = make_payment(status=PaymentStatus.ABANDONED, failure_reason=FailureReason.CHECKOUT_ABANDONED)
    action, _ = select_action(case, payment, make_customer(), None)
    assert action == RecoveryAction.SEND_PAYMENT_REMINDER


def test_select_action_subscription_failure_first_attempt():
    case = make_case(failure_category=FailureCategory.SUBSCRIPTION_FAILURE)
    payment = make_payment(retry_count=0, subscription_id="sub_test")
    subscription = make_subscription(status=SubscriptionStatus.PAST_DUE)
    action, _ = select_action(case, payment, make_customer(), subscription)
    assert action == RecoveryAction.RETRY_PAYMENT


def test_select_action_subscription_failure_already_retried():
    case = make_case(failure_category=FailureCategory.SUBSCRIPTION_FAILURE)
    payment = make_payment(retry_count=1, subscription_id="sub_test")
    subscription = make_subscription(status=SubscriptionStatus.PAST_DUE)
    action, _ = select_action(case, payment, make_customer(), subscription)
    assert action == RecoveryAction.REQUEST_PAYMENT_METHOD_UPDATE


def test_select_action_canceled_subscription_escalates():
    case = make_case(failure_category=FailureCategory.SUBSCRIPTION_FAILURE)
    payment = make_payment(retry_count=0, subscription_id="sub_test")
    subscription = make_subscription(status=SubscriptionStatus.CANCELED)
    action, _ = select_action(case, payment, make_customer(), subscription)
    assert action == RecoveryAction.ESCALATE


def test_select_action_repeated_failure_reasonable_history():
    case = make_case(failure_category=FailureCategory.REPEATED_FAILURE, amount_at_risk=500.0)
    payment = make_payment(retry_count=2)
    customer = make_customer(success=7, failed=3)  # 70% success rate
    action, _ = select_action(case, payment, customer, None)
    assert action == RecoveryAction.REQUEST_PAYMENT_METHOD_UPDATE


def test_select_action_repeated_failure_weak_history_escalates():
    case = make_case(failure_category=FailureCategory.REPEATED_FAILURE, amount_at_risk=500.0)
    payment = make_payment(retry_count=2)
    customer = make_customer(success=1, failed=9)  # 10% success rate
    action, _ = select_action(case, payment, customer, None)
    assert action == RecoveryAction.ESCALATE


def test_select_action_repeated_failure_high_value_escalates():
    case = make_case(failure_category=FailureCategory.REPEATED_FAILURE, amount_at_risk=HIGH_RISK_ESCALATION_AMOUNT + 1)
    payment = make_payment(retry_count=2)
    customer = make_customer(success=9, failed=1)  # strong history, but amount is still risky
    action, _ = select_action(case, payment, customer, None)
    assert action == RecoveryAction.ESCALATE


def test_select_action_retry_limit_exceeded_escalates():
    case = make_case(failure_category=FailureCategory.TEMPORARY_FAILURE)
    payment = make_payment(retry_count=MAX_RETRY_CAP)
    action, reason = select_action(case, payment, make_customer(), None)
    assert action == RecoveryAction.ESCALATE
    assert "retried" in reason


def test_select_action_recovery_attempts_exhausted_escalates():
    case = make_case(failure_category=FailureCategory.TEMPORARY_FAILURE, recovery_attempts=RECOVERY_ATTEMPT_CAP)
    payment = make_payment(retry_count=0)
    action, reason = select_action(case, payment, make_customer(), None)
    assert action == RecoveryAction.ESCALATE
    assert "attempt" in reason


# ---------------------------------------------------------------------------
# Safety validation
# ---------------------------------------------------------------------------


def test_validate_rejects_missing_action():
    case = make_case(action=None)
    payment = make_payment()
    allowed, reason = validate_safety(case, payment, make_customer(), None)
    assert allowed is False
    assert "missing" in reason


def test_validate_rejects_already_recovered_case():
    case = make_case(status=RecoveryCaseStatus.RECOVERED, action=RecoveryAction.RETRY_PAYMENT)
    payment = make_payment()
    allowed, reason = validate_safety(case, payment, make_customer(), None)
    assert allowed is False
    assert "recovered" in reason


def test_validate_rejects_already_succeeded_payment():
    case = make_case(action=RecoveryAction.RETRY_PAYMENT)
    payment = make_payment(status=PaymentStatus.SUCCESS, failure_reason=None)
    allowed, reason = validate_safety(case, payment, make_customer(), None)
    assert allowed is False
    assert "already succeeded" in reason


def test_validate_rejects_retry_over_limit():
    case = make_case(action=RecoveryAction.RETRY_PAYMENT)
    payment = make_payment(retry_count=MAX_RETRY_CAP)
    allowed, reason = validate_safety(case, payment, make_customer(), None)
    assert allowed is False
    assert "Retry limit" in reason


def test_validate_rejects_retry_on_canceled_subscription():
    case = make_case(failure_category=FailureCategory.SUBSCRIPTION_FAILURE, action=RecoveryAction.RETRY_PAYMENT)
    payment = make_payment(subscription_id="sub_test", retry_count=0)
    subscription = make_subscription(status=SubscriptionStatus.CANCELED)
    allowed, reason = validate_safety(case, payment, make_customer(), subscription)
    assert allowed is False
    assert "canceled" in reason


def test_validate_rejects_action_not_allowed_for_category():
    case = make_case(failure_category=FailureCategory.ABANDONED_CHECKOUT, action=RecoveryAction.RETRY_PAYMENT)
    payment = make_payment(status=PaymentStatus.ABANDONED, failure_reason=FailureReason.CHECKOUT_ABANDONED)
    allowed, reason = validate_safety(case, payment, make_customer(), None)
    assert allowed is False
    assert "not an allowed action" in reason


def test_validate_allows_a_valid_action():
    case = make_case(failure_category=FailureCategory.TEMPORARY_FAILURE, action=RecoveryAction.RETRY_PAYMENT)
    payment = make_payment(retry_count=1)
    allowed, reason = validate_safety(case, payment, make_customer(), None)
    assert allowed is True
    assert reason is None


def test_validate_always_allows_escalate():
    case = make_case(failure_category=FailureCategory.ABANDONED_CHECKOUT, action=RecoveryAction.ESCALATE)
    payment = make_payment(status=PaymentStatus.ABANDONED, failure_reason=FailureReason.CHECKOUT_ABANDONED)
    allowed, _ = validate_safety(case, payment, make_customer(), None)
    assert allowed is True


# ---------------------------------------------------------------------------
# Simulated execution
# ---------------------------------------------------------------------------


def test_simulate_retry_payment_success_for_strong_history():
    case = make_case(action=RecoveryAction.RETRY_PAYMENT, amount_at_risk=1000.0)
    payment = make_payment(retry_count=1)
    customer = make_customer(success=9, failed=1)  # 90% success rate
    result = simulate_execution(case, payment, customer)
    assert result["execution_status"] == "success"
    assert result["new_status"] == RecoveryCaseStatus.RECOVERED
    assert result["recovered_amount"] == 1000.0


def test_simulate_retry_payment_failure_for_weak_history():
    case = make_case(action=RecoveryAction.RETRY_PAYMENT, amount_at_risk=1000.0)
    payment = make_payment(retry_count=1)
    customer = make_customer(success=1, failed=9)  # 10% success rate
    result = simulate_execution(case, payment, customer)
    assert result["execution_status"] == "failed"
    assert result["new_status"] == RecoveryCaseStatus.FAILED
    assert result["recovered_amount"] == 0.0
    assert result["failure_reason"]


def test_simulate_schedule_retry():
    case = make_case(action=RecoveryAction.SCHEDULE_RETRY)
    result = simulate_execution(case, make_payment(), make_customer())
    assert result["execution_status"] == "scheduled"
    assert result["new_status"] == RecoveryCaseStatus.FAILED
    assert result["recovered_amount"] == 0.0


def test_simulate_send_payment_reminder():
    case = make_case(action=RecoveryAction.SEND_PAYMENT_REMINDER)
    result = simulate_execution(case, make_payment(), make_customer())
    assert result["execution_status"] == "pending_customer_action"
    assert result["new_status"] == RecoveryCaseStatus.FAILED


def test_simulate_request_payment_method_update():
    case = make_case(action=RecoveryAction.REQUEST_PAYMENT_METHOD_UPDATE)
    result = simulate_execution(case, make_payment(), make_customer())
    assert result["execution_status"] == "action_required"
    assert result["new_status"] == RecoveryCaseStatus.FAILED


def test_simulate_escalate():
    case = make_case(action=RecoveryAction.ESCALATE)
    result = simulate_execution(case, make_payment(), make_customer())
    assert result["execution_status"] == "escalated"
    assert result["new_status"] == RecoveryCaseStatus.ESCALATED
    assert result["recovered_amount"] == 0.0


def test_simulation_is_deterministic():
    case = make_case(action=RecoveryAction.RETRY_PAYMENT, amount_at_risk=750.0)
    payment = make_payment(retry_count=0)
    customer = make_customer(success=8, failed=2)
    result_a = simulate_execution(case, payment, customer)
    result_b = simulate_execution(case, payment, customer)
    assert result_a == result_b


def test_recovered_amount_never_exceeds_amount_at_risk():
    case = make_case(action=RecoveryAction.RETRY_PAYMENT, amount_at_risk=250.0)
    payment = make_payment(amount=250.0, retry_count=0)
    customer = make_customer(success=10, failed=0)
    result = simulate_execution(case, payment, customer)
    assert result["recovered_amount"] <= 250.0
