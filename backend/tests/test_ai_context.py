from datetime import date, datetime

from app.ai.context import build_context
from app.models import (
    Customer,
    FailureCategory,
    FailureReason,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryPriority,
    Subscription,
    SubscriptionStatus,
)


def _build_case(with_subscription=False):
    customer = Customer(
        customer_id="cus_ctx",
        customer_since=date(2024, 1, 1),
        total_successful_payments=8,
        total_failed_payments=2,
        lifetime_value=5000.0,
        created_at=datetime.utcnow(),
    )
    subscription = None
    subscription_id = None
    if with_subscription:
        subscription = Subscription(
            subscription_id="sub_ctx",
            customer_id="cus_ctx",
            plan="standard",
            amount=599.0,
            status=SubscriptionStatus.PAST_DUE,
            next_payment_date=None,
            created_at=datetime(2024, 1, 1),
        )
        subscription_id = "sub_ctx"

    payment = Payment(
        payment_id="pay_ctx",
        customer_id="cus_ctx",
        subscription_id=subscription_id,
        amount=1500.0,
        currency="INR",
        payment_status=PaymentStatus.FAILED,
        failure_reason=FailureReason.TEMPORARY_FAILURE,
        payment_method=PaymentMethod.CARD,
        created_at=datetime(2024, 1, 1),
        retry_count=1,
    )
    payment.subscription = subscription
    payment.customer = customer

    case = RecoveryCase(
        recovery_case_id="rec_ctx",
        payment_id="pay_ctx",
        customer_id="cus_ctx",
        status=RecoveryCaseStatus.DETECTED.value,
        priority=RecoveryPriority.MEDIUM,
        amount_at_risk=1500.0,
        customer_value=5000.0,
        failure_category=FailureCategory.TEMPORARY_FAILURE,
        detection_reason="test detection reason",
        recommended_next_step="retry_payment",
        recovery_attempts=0,
    )
    case.payment = payment
    case.customer = customer
    return case


def test_context_contains_expected_fields():
    case = _build_case()
    context = build_context(case)

    expected_keys = {
        "payment_amount",
        "currency",
        "payment_status",
        "failure_reason",
        "failure_category",
        "retry_count",
        "customer_total_successful_payments",
        "customer_total_failed_payments",
        "customer_success_rate",
        "customer_lifetime_value",
        "subscription_status",
        "recovery_priority",
        "amount_at_risk",
        "recovery_attempts_so_far",
        "deterministic_recommended_action",
        "previously_planned_action",
    }
    assert expected_keys.issubset(context.keys())
    assert context["payment_amount"] == 1500.0
    assert context["customer_success_rate"] == 0.8
    assert context["subscription_status"] is None


def test_context_includes_subscription_status_when_present():
    case = _build_case(with_subscription=True)
    context = build_context(case)
    assert context["subscription_status"] == "past_due"


def test_context_has_no_pii_fields():
    case = _build_case()
    context = build_context(case)
    forbidden = {"name", "email", "phone", "address", "customer_id", "payment_id"}
    assert forbidden.isdisjoint(context.keys())


def test_context_is_compact():
    case = _build_case()
    context = build_context(case)
    # Sanity bound: a 3B local model needs a small, controlled context.
    assert len(context) <= 20
