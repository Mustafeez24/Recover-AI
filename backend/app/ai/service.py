"""Phase 5 orchestration.

CRITICAL PRINCIPLE, enforced by this module's design, not just by
convention: AI recommends. Deterministic safety logic (reused straight
from Phase 4, see app.recovery.action_rules.validate_safety) validates.
The Phase 4 recovery engine executes -- nothing in this module ever
calls plan_action/validate_action_step/execute_action or otherwise
mutates a RecoveryCase's state or money fields. An AI recommendation is
purely advisory and is only ever recorded, never acted on automatically.
"""

import json
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.context import build_context
from app.ai.ollama_provider import OllamaProvider
from app.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from app.ai.provider import (
    AIProvider,
    AIProviderResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)
from app.ai.schemas import AIRecommendationOutput
from app.core.config import settings
from app.models import AIRecommendation, RecoveryCase
from app.recovery.action_rules import select_action, validate_safety

# How much of the model's raw response to keep for the audit trail --
# bounded so a misbehaving response can't bloat the database.
_RAW_RESPONSE_STORE_LIMIT = 1000


def get_default_provider() -> AIProvider:
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout_seconds,
    )


def get_ai_recommendation(provider: AIProvider, case: RecoveryCase) -> dict:
    """Calls the provider and validates its output. Never raises -- every
    failure mode (unavailable, timeout, bad response, invalid JSON,
    schema violation) comes back as a status string instead, so a single
    AI call failing never breaks the caller."""
    context = build_context(case)
    user_prompt = build_user_prompt(context)

    try:
        raw = provider.complete(SYSTEM_PROMPT, user_prompt)
    except AIProviderUnavailableError as exc:
        return {"status": "unavailable", "recommendation": None, "error": str(exc), "raw_response": None}
    except AIProviderTimeoutError as exc:
        return {"status": "timeout", "recommendation": None, "error": str(exc), "raw_response": None}
    except AIProviderResponseError as exc:
        return {"status": "provider_error", "recommendation": None, "error": str(exc), "raw_response": None}

    raw_stored = raw[:_RAW_RESPONSE_STORE_LIMIT]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"status": "invalid_json", "recommendation": None, "error": str(exc), "raw_response": raw_stored}

    try:
        recommendation = AIRecommendationOutput.model_validate(parsed)
    except ValidationError as exc:
        return {"status": "invalid_schema", "recommendation": None, "error": str(exc), "raw_response": raw_stored}

    return {"status": "ok", "recommendation": recommendation, "error": None, "raw_response": raw_stored}


def analyze_opportunity(session: Session, provider: AIProvider, case: RecoveryCase) -> dict:
    """The full Phase 5 flow for one opportunity: build context, call the
    AI, compare against the Phase 4 deterministic action, run the AI's
    suggestion through the same safety validator real actions use, and
    persist the outcome. Returns a dict describing everything -- but never
    plans, validates, or executes anything against the RecoveryCase
    itself. That stays entirely Phase 4's job."""
    payment = case.payment
    customer = case.customer
    subscription = payment.subscription

    deterministic_action, deterministic_reason = select_action(case, payment, customer, subscription)

    ai_result = get_ai_recommendation(provider, case)
    recommendation = ai_result["recommendation"]

    agreement = None
    safety_result = None
    safety_reason = None
    fallback_used = True
    effective_action = deterministic_action

    if recommendation is not None:
        agreement = recommendation.recommended_action == deterministic_action
        allowed, rejection_reason = validate_safety(
            case, payment, customer, subscription, action_override=recommendation.recommended_action
        )
        safety_result = "passed" if allowed else "rejected"
        safety_reason = rejection_reason
        if allowed:
            fallback_used = False
            effective_action = recommendation.recommended_action

    record = AIRecommendation(
        recovery_case_id=case.recovery_case_id,
        ai_recommended_action=recommendation.recommended_action.value if recommendation else None,
        ai_confidence=recommendation.confidence if recommendation else None,
        ai_reason=recommendation.reason if recommendation else None,
        ai_risk_level=recommendation.risk_level.value if recommendation else None,
        ai_customer_context=recommendation.customer_context if recommendation else None,
        ai_alternative_action=(
            recommendation.alternative_action.value
            if recommendation and recommendation.alternative_action
            else None
        ),
        ai_status=ai_result["status"],
        ai_model=getattr(provider, "model", "unknown"),
        ai_generated_at=datetime.utcnow(),
        deterministic_action=deterministic_action.value,
        safety_validation_result=safety_result,
        safety_rejection_reason=safety_reason,
        agreement=agreement,
        fallback_used=fallback_used,
        effective_action=effective_action.value,
    )
    session.add(record)
    session.commit()

    return {
        "recovery_case_id": case.recovery_case_id,
        "deterministic_action": deterministic_action.value,
        "deterministic_reason": deterministic_reason,
        "ai_status": ai_result["status"],
        "ai_error": ai_result["error"],
        "ai_recommended_action": recommendation.recommended_action.value if recommendation else None,
        "ai_confidence": recommendation.confidence if recommendation else None,
        "ai_reason": recommendation.reason if recommendation else None,
        "ai_risk_level": recommendation.risk_level.value if recommendation else None,
        "ai_customer_context": recommendation.customer_context if recommendation else None,
        "ai_alternative_action": (
            recommendation.alternative_action.value
            if recommendation and recommendation.alternative_action
            else None
        ),
        "agreement": agreement,
        "safety_validation_result": safety_result,
        "safety_rejection_reason": safety_reason,
        "fallback_used": fallback_used,
        "effective_action": effective_action.value,
        "ai_model": record.ai_model,
    }


def get_ai_summary(session: Session, provider: AIProvider = None) -> dict:
    cases_analyzed = (
        session.execute(select(func.count(func.distinct(AIRecommendation.recovery_case_id)))).scalar() or 0
    )
    total_runs = session.execute(select(func.count()).select_from(AIRecommendation)).scalar() or 0
    successful = (
        session.execute(
            select(func.count()).select_from(AIRecommendation).where(AIRecommendation.ai_status == "ok")
        ).scalar()
        or 0
    )
    failures = total_runs - successful
    agreements = (
        session.execute(
            select(func.count()).select_from(AIRecommendation).where(AIRecommendation.agreement.is_(True))
        ).scalar()
        or 0
    )
    disagreements = (
        session.execute(
            select(func.count()).select_from(AIRecommendation).where(AIRecommendation.agreement.is_(False))
        ).scalar()
        or 0
    )
    rejected = (
        session.execute(
            select(func.count())
            .select_from(AIRecommendation)
            .where(AIRecommendation.safety_validation_result == "rejected")
        ).scalar()
        or 0
    )
    fallback_count = (
        session.execute(
            select(func.count()).select_from(AIRecommendation).where(AIRecommendation.fallback_used.is_(True))
        ).scalar()
        or 0
    )
    avg_confidence = session.execute(
        select(func.avg(AIRecommendation.ai_confidence)).where(AIRecommendation.ai_confidence.isnot(None))
    ).scalar()

    by_action = dict(
        session.execute(
            select(AIRecommendation.ai_recommended_action, func.count())
            .where(AIRecommendation.ai_recommended_action.isnot(None))
            .group_by(AIRecommendation.ai_recommended_action)
        ).all()
    )
    by_risk = dict(
        session.execute(
            select(AIRecommendation.ai_risk_level, func.count())
            .where(AIRecommendation.ai_risk_level.isnot(None))
            .group_by(AIRecommendation.ai_risk_level)
        ).all()
    )

    result = {
        "cases_analyzed": cases_analyzed,
        "total_ai_calls": total_runs,
        "successful_recommendations": successful,
        "ai_failures": failures,
        "agreements": agreements,
        "disagreements": disagreements,
        "rejected_recommendations": rejected,
        "fallback_count": fallback_count,
        "average_confidence": round(float(avg_confidence), 3) if avg_confidence is not None else None,
        "recommendations_by_action": by_action,
        "recommendations_by_risk_level": by_risk,
    }

    if provider is not None:
        result["ollama_available"] = provider.is_available()

    return result
