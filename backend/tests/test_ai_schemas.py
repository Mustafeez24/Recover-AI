import pytest
from pydantic import ValidationError

from app.ai.schemas import AIRecommendationOutput, RiskLevel
from app.models import RecoveryAction


def test_valid_ai_response():
    rec = AIRecommendationOutput(
        recommended_action="RETRY_PAYMENT",
        confidence=0.82,
        reason="The customer has a strong payment history and the failure appears temporary.",
        risk_level="LOW",
        customer_context="Customer has successfully completed most previous payments.",
        alternative_action="SCHEDULE_RETRY",
    )
    assert rec.recommended_action == RecoveryAction.RETRY_PAYMENT
    assert rec.risk_level == RiskLevel.LOW
    assert rec.alternative_action == RecoveryAction.SCHEDULE_RETRY


def test_action_casing_is_normalized():
    rec = AIRecommendationOutput(
        recommended_action="retry_payment",
        confidence=0.5,
        reason="ok",
        risk_level="low",
        customer_context="ok",
    )
    assert rec.recommended_action == RecoveryAction.RETRY_PAYMENT
    assert rec.risk_level == RiskLevel.LOW


def test_alternative_action_optional_and_defaults_to_none():
    rec = AIRecommendationOutput(
        recommended_action="ESCALATE",
        confidence=0.9,
        reason="ok",
        risk_level="HIGH",
        customer_context="ok",
    )
    assert rec.alternative_action is None


def test_unsupported_action_rejected():
    with pytest.raises(ValidationError):
        AIRecommendationOutput(
            recommended_action="REFUND_CUSTOMER",  # not one of the 5 allowed actions
            confidence=0.5,
            reason="ok",
            risk_level="LOW",
            customer_context="ok",
        )


def test_unsupported_alternative_action_rejected():
    with pytest.raises(ValidationError):
        AIRecommendationOutput(
            recommended_action="RETRY_PAYMENT",
            confidence=0.5,
            reason="ok",
            risk_level="LOW",
            customer_context="ok",
            alternative_action="CANCEL_SUBSCRIPTION",
        )


def test_missing_required_fields_rejected():
    with pytest.raises(ValidationError):
        AIRecommendationOutput(recommended_action="RETRY_PAYMENT")


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        AIRecommendationOutput(
            recommended_action="RETRY_PAYMENT",
            confidence=1.5,
            reason="ok",
            risk_level="LOW",
            customer_context="ok",
        )


def test_negative_confidence_rejected():
    with pytest.raises(ValidationError):
        AIRecommendationOutput(
            recommended_action="RETRY_PAYMENT",
            confidence=-0.1,
            reason="ok",
            risk_level="LOW",
            customer_context="ok",
        )


def test_invalid_risk_level_rejected():
    with pytest.raises(ValidationError):
        AIRecommendationOutput(
            recommended_action="RETRY_PAYMENT",
            confidence=0.5,
            reason="ok",
            risk_level="EXTREME",
            customer_context="ok",
        )


def test_empty_reason_rejected():
    with pytest.raises(ValidationError):
        AIRecommendationOutput(
            recommended_action="RETRY_PAYMENT",
            confidence=0.5,
            reason="",
            risk_level="LOW",
            customer_context="ok",
        )


def test_overlong_reason_rejected():
    with pytest.raises(ValidationError):
        AIRecommendationOutput(
            recommended_action="RETRY_PAYMENT",
            confidence=0.5,
            reason="x" * 501,
            risk_level="LOW",
            customer_context="ok",
        )
