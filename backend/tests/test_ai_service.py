from datetime import date, datetime

from app.ai.provider import AIProvider, AIProviderResponseError, AIProviderTimeoutError, AIProviderUnavailableError
from app.ai.service import analyze_opportunity, get_ai_recommendation, get_ai_summary
from app.models import (
    AIRecommendation,
    Customer,
    FailureCategory,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RecoveryAction,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryPriority,
    SubscriptionStatus,
)


class FakeAIProvider(AIProvider):
    """Deterministic stand-in for Ollama -- no live server involved."""

    def __init__(self, response_text=None, raise_error=None, available=True, model="fake-model"):
        self.response_text = response_text
        self.raise_error = raise_error
        self.available = available
        self.model = model
        self.calls = []

    def complete(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if self.raise_error:
            raise self.raise_error
        return self.response_text

    def is_available(self):
        return self.available


VALID_JSON = """{
  "recommended_action": "RETRY_PAYMENT",
  "confidence": 0.82,
  "reason": "Temporary failure with a strong customer history.",
  "risk_level": "LOW",
  "customer_context": "Customer has a strong payment history.",
  "alternative_action": "SCHEDULE_RETRY"
}"""


def _add_customer(db, customer_id="cus_ai", success=8, failed=2, lifetime_value=5000.0):
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


def _add_payment(db, payment_id, customer_id, amount=1000.0, retry_count=0, status=PaymentStatus.FAILED):
    p = Payment(
        payment_id=payment_id,
        customer_id=customer_id,
        subscription_id=None,
        amount=amount,
        currency="INR",
        payment_status=status,
        failure_reason=None,
        payment_method=PaymentMethod.CARD,
        created_at=datetime(2024, 1, 1),
        retry_count=retry_count,
    )
    db.add(p)
    db.commit()
    return p


def _add_case(
    db,
    case_id,
    payment_id,
    customer_id,
    failure_category=FailureCategory.TEMPORARY_FAILURE,
    amount_at_risk=1000.0,
    priority=RecoveryPriority.MEDIUM,
):
    case = RecoveryCase(
        recovery_case_id=case_id,
        payment_id=payment_id,
        customer_id=customer_id,
        status=RecoveryCaseStatus.DETECTED.value,
        priority=priority,
        amount_at_risk=amount_at_risk,
        customer_value=5000.0,
        failure_category=failure_category,
        detection_reason="test",
        recommended_next_step="test",
        created_at=datetime.utcnow(),
    )
    db.add(case)
    db.commit()
    return case


# ---------------------------------------------------------------------------
# get_ai_recommendation -- provider-failure handling
# ---------------------------------------------------------------------------


def test_get_ai_recommendation_valid_response(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai1", customer.customer_id)
    case = _add_case(db_session, "rec_ai1", payment.payment_id, customer.customer_id)

    provider = FakeAIProvider(response_text=VALID_JSON)
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "ok"
    assert result["recommendation"].recommended_action == RecoveryAction.RETRY_PAYMENT
    assert result["error"] is None


def test_get_ai_recommendation_invalid_json(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai2", customer.customer_id)
    case = _add_case(db_session, "rec_ai2", payment.payment_id, customer.customer_id)

    provider = FakeAIProvider(response_text="not valid json {{{")
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "invalid_json"
    assert result["recommendation"] is None


def test_get_ai_recommendation_unsupported_action(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai3", customer.customer_id)
    case = _add_case(db_session, "rec_ai3", payment.payment_id, customer.customer_id)

    bad_json = VALID_JSON.replace("RETRY_PAYMENT", "REFUND_MONEY")
    provider = FakeAIProvider(response_text=bad_json)
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "invalid_schema"
    assert result["recommendation"] is None


def test_get_ai_recommendation_missing_fields(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai4", customer.customer_id)
    case = _add_case(db_session, "rec_ai4", payment.payment_id, customer.customer_id)

    provider = FakeAIProvider(response_text='{"recommended_action": "RETRY_PAYMENT"}')
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "invalid_schema"


def test_get_ai_recommendation_invalid_confidence(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai5", customer.customer_id)
    case = _add_case(db_session, "rec_ai5", payment.payment_id, customer.customer_id)

    bad_json = VALID_JSON.replace('"confidence": 0.82', '"confidence": 3.0')
    provider = FakeAIProvider(response_text=bad_json)
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "invalid_schema"


def test_get_ai_recommendation_invalid_risk_level(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai6", customer.customer_id)
    case = _add_case(db_session, "rec_ai6", payment.payment_id, customer.customer_id)

    bad_json = VALID_JSON.replace('"risk_level": "LOW"', '"risk_level": "SEVERE"')
    provider = FakeAIProvider(response_text=bad_json)
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "invalid_schema"


def test_get_ai_recommendation_provider_unavailable(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai7", customer.customer_id)
    case = _add_case(db_session, "rec_ai7", payment.payment_id, customer.customer_id)

    provider = FakeAIProvider(raise_error=AIProviderUnavailableError("connection refused"))
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "unavailable"
    assert result["recommendation"] is None


def test_get_ai_recommendation_provider_timeout(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai8", customer.customer_id)
    case = _add_case(db_session, "rec_ai8", payment.payment_id, customer.customer_id)

    provider = FakeAIProvider(raise_error=AIProviderTimeoutError("timed out"))
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "timeout"


def test_get_ai_recommendation_provider_response_error(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai9", customer.customer_id)
    case = _add_case(db_session, "rec_ai9", payment.payment_id, customer.customer_id)

    provider = FakeAIProvider(raise_error=AIProviderResponseError("model not found"))
    result = get_ai_recommendation(provider, case)

    assert result["status"] == "provider_error"


# ---------------------------------------------------------------------------
# analyze_opportunity -- agreement, disagreement, safety, fallback, persistence
# ---------------------------------------------------------------------------


def test_analyze_opportunity_agreement(db_session):
    customer = _add_customer(db_session, success=9, failed=1)
    payment = _add_payment(db_session, "pay_ai10", customer.customer_id, amount=1000.0)
    # TEMPORARY_FAILURE always deterministically selects RETRY_PAYMENT.
    case = _add_case(db_session, "rec_ai10", payment.payment_id, customer.customer_id, amount_at_risk=1000.0)

    provider = FakeAIProvider(response_text=VALID_JSON)  # also recommends RETRY_PAYMENT
    result = analyze_opportunity(db_session, provider, case)

    assert result["deterministic_action"] == "retry_payment"
    assert result["ai_recommended_action"] == "retry_payment"
    assert result["agreement"] is True
    assert result["safety_validation_result"] == "passed"
    assert result["fallback_used"] is False
    assert result["effective_action"] == "retry_payment"


def test_analyze_opportunity_disagreement(db_session):
    customer = _add_customer(db_session, success=9, failed=1)
    payment = _add_payment(db_session, "pay_ai11", customer.customer_id, amount=1000.0)
    case = _add_case(db_session, "rec_ai11", payment.payment_id, customer.customer_id, amount_at_risk=1000.0)

    ai_json = VALID_JSON.replace("RETRY_PAYMENT", "SCHEDULE_RETRY", 1)
    provider = FakeAIProvider(response_text=ai_json)
    result = analyze_opportunity(db_session, provider, case)

    assert result["deterministic_action"] == "retry_payment"
    assert result["ai_recommended_action"] == "schedule_retry"
    assert result["agreement"] is False
    # schedule_retry IS allowed for temporary_failure, so it still passes safety.
    assert result["safety_validation_result"] == "passed"
    assert result["fallback_used"] is False


def test_analyze_opportunity_rejects_unsafe_ai_recommendation_and_falls_back(db_session):
    customer = _add_customer(db_session, success=9, failed=1)
    payment = _add_payment(db_session, "pay_ai12", customer.customer_id, amount=1000.0)
    # ABANDONED_CHECKOUT only allows SEND_PAYMENT_REMINDER -- RETRY_PAYMENT
    # is not a safe/allowed action for this category.
    case = _add_case(
        db_session,
        "rec_ai12",
        payment.payment_id,
        customer.customer_id,
        failure_category=FailureCategory.ABANDONED_CHECKOUT,
        amount_at_risk=1000.0,
    )

    provider = FakeAIProvider(response_text=VALID_JSON)  # recommends RETRY_PAYMENT
    result = analyze_opportunity(db_session, provider, case)

    assert result["ai_recommended_action"] == "retry_payment"
    assert result["safety_validation_result"] == "rejected"
    assert result["fallback_used"] is True
    assert result["effective_action"] == result["deterministic_action"]
    assert result["effective_action"] == "send_payment_reminder"


def test_analyze_opportunity_falls_back_when_ai_unavailable(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai13", customer.customer_id)
    case = _add_case(db_session, "rec_ai13", payment.payment_id, customer.customer_id)

    provider = FakeAIProvider(raise_error=AIProviderUnavailableError("down"))
    result = analyze_opportunity(db_session, provider, case)

    assert result["ai_status"] == "unavailable"
    assert result["ai_recommended_action"] is None
    assert result["agreement"] is None
    assert result["fallback_used"] is True
    assert result["effective_action"] == result["deterministic_action"]


def test_analyze_opportunity_escalation_scenario(db_session):
    customer = _add_customer(db_session, success=1, failed=9)  # weak history
    payment = _add_payment(db_session, "pay_ai14", customer.customer_id, amount=6000.0, retry_count=2)
    case = _add_case(
        db_session,
        "rec_ai14",
        payment.payment_id,
        customer.customer_id,
        failure_category=FailureCategory.REPEATED_FAILURE,
        amount_at_risk=6000.0,
    )

    escalate_json = VALID_JSON.replace("RETRY_PAYMENT", "ESCALATE", 1).replace(
        '"alternative_action": "SCHEDULE_RETRY"', '"alternative_action": null'
    )
    provider = FakeAIProvider(response_text=escalate_json)
    result = analyze_opportunity(db_session, provider, case)

    assert result["deterministic_action"] == "escalate"
    assert result["ai_recommended_action"] == "escalate"
    assert result["agreement"] is True
    assert result["safety_validation_result"] == "passed"


def test_analyze_opportunity_does_not_mutate_case_state(db_session):
    """The AI layer must never plan/validate/execute -- only Phase 4 does."""
    customer = _add_customer(db_session, success=9, failed=1)
    payment = _add_payment(db_session, "pay_ai15", customer.customer_id, amount=1000.0)
    case = _add_case(db_session, "rec_ai15", payment.payment_id, customer.customer_id, amount_at_risk=1000.0)

    provider = FakeAIProvider(response_text=VALID_JSON)
    analyze_opportunity(db_session, provider, case)

    assert case.status == RecoveryCaseStatus.DETECTED.value
    assert case.action is None
    assert float(case.recovered_amount or 0) == 0.0


def test_analyze_opportunity_persists_ai_recommendation(db_session):
    customer = _add_customer(db_session, success=9, failed=1)
    payment = _add_payment(db_session, "pay_ai16", customer.customer_id, amount=1000.0)
    case = _add_case(db_session, "rec_ai16", payment.payment_id, customer.customer_id, amount_at_risk=1000.0)

    provider = FakeAIProvider(response_text=VALID_JSON, model="qwen2.5:3b")
    analyze_opportunity(db_session, provider, case)

    stored = db_session.query(AIRecommendation).filter_by(recovery_case_id=case.recovery_case_id).one()
    assert stored.ai_status == "ok"
    assert stored.ai_recommended_action == "retry_payment"
    assert stored.ai_model == "qwen2.5:3b"
    assert stored.deterministic_action == "retry_payment"
    assert stored.agreement is True


def test_analyze_opportunity_persists_failure_record_too(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_ai17", customer.customer_id)
    case = _add_case(db_session, "rec_ai17", payment.payment_id, customer.customer_id)

    provider = FakeAIProvider(raise_error=AIProviderTimeoutError("timed out"))
    analyze_opportunity(db_session, provider, case)

    stored = db_session.query(AIRecommendation).filter_by(recovery_case_id=case.recovery_case_id).one()
    assert stored.ai_status == "timeout"
    assert stored.ai_recommended_action is None
    assert stored.fallback_used is True


# ---------------------------------------------------------------------------
# get_ai_summary
# ---------------------------------------------------------------------------


def test_ai_summary_empty(db_session):
    summary = get_ai_summary(db_session)
    assert summary["cases_analyzed"] == 0
    assert summary["successful_recommendations"] == 0
    assert summary["average_confidence"] is None


def test_ai_summary_reflects_agreement_and_disagreement(db_session):
    customer = _add_customer(db_session, success=9, failed=1)

    p1 = _add_payment(db_session, "pay_ai18", customer.customer_id, amount=1000.0)
    c1 = _add_case(db_session, "rec_ai18", p1.payment_id, customer.customer_id, amount_at_risk=1000.0)
    analyze_opportunity(db_session, FakeAIProvider(response_text=VALID_JSON), c1)

    p2 = _add_payment(db_session, "pay_ai19", customer.customer_id, amount=1000.0)
    c2 = _add_case(db_session, "rec_ai19", p2.payment_id, customer.customer_id, amount_at_risk=1000.0)
    disagree_json = VALID_JSON.replace("RETRY_PAYMENT", "SCHEDULE_RETRY", 1)
    analyze_opportunity(db_session, FakeAIProvider(response_text=disagree_json), c2)

    summary = get_ai_summary(db_session)
    assert summary["cases_analyzed"] == 2
    assert summary["successful_recommendations"] == 2
    assert summary["agreements"] == 1
    assert summary["disagreements"] == 1
    assert summary["average_confidence"] == 0.82
    assert summary["recommendations_by_action"]["retry_payment"] == 1
    assert summary["recommendations_by_action"]["schedule_retry"] == 1


def test_ai_summary_includes_availability_when_provider_given(db_session):
    provider = FakeAIProvider(available=False)
    summary = get_ai_summary(db_session, provider)
    assert summary["ollama_available"] is False
