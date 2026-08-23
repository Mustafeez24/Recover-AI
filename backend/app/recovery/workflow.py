"""Recovery workflow orchestration: plan -> validate -> execute, each step
driving the RecoveryCase through `app.recovery.state_machine` and writing
an audit-trail row to `recovery_action_history`. Every function here is
idempotent -- calling any of them again on a case that has already moved
past the relevant step returns the existing result instead of redoing
(or duplicating) the work.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import RecoveryAction, RecoveryActionHistory, RecoveryCase, RecoveryCaseStatus
from app.recovery.action_rules import RECOVERY_ATTEMPT_CAP, select_action, simulate_execution, validate_safety
from app.recovery.state_machine import TERMINAL_STATES, transition


def _record_history(session, case, *, action, previous_state, new_state, reason, validation_result=None, execution_result=None, amount=None):
    entry = RecoveryActionHistory(
        recovery_case_id=case.recovery_case_id,
        action=action,
        previous_state=previous_state,
        new_state=new_state,
        reason=reason,
        validation_result=validation_result,
        execution_result=execution_result,
        amount=amount,
        created_at=datetime.utcnow(),
    )
    session.add(entry)


# ---------------------------------------------------------------------------
# 1. Plan
# ---------------------------------------------------------------------------


def plan_action(session: Session, case: RecoveryCase) -> dict:
    if case.status not in (RecoveryCaseStatus.DETECTED.value, RecoveryCaseStatus.FAILED.value):
        return {
            "already_planned": True,
            "action": case.action,
            "reason": case.action_reason,
            "status": case.status,
        }

    previous_state = case.status

    if case.status == RecoveryCaseStatus.FAILED.value and (case.recovery_attempts or 0) >= RECOVERY_ATTEMPT_CAP:
        reason = (
            f"{case.recovery_attempts} recovery attempt(s) already made (limit {RECOVERY_ATTEMPT_CAP}); "
            "no further automated planning."
        )
        transition(case, RecoveryCaseStatus.EXHAUSTED)
        _record_history(
            session, case, action=case.action, previous_state=previous_state, new_state=case.status, reason=reason
        )
        session.commit()
        return {"already_planned": False, "action": case.action, "reason": reason, "status": case.status}

    payment = case.payment
    customer = case.customer
    subscription = payment.subscription

    action, reason = select_action(case, payment, customer, subscription)
    case.action = action.value
    case.action_reason = reason
    case.planned_at = datetime.utcnow()

    if previous_state == RecoveryCaseStatus.FAILED.value and action == RecoveryAction.ESCALATE:
        transition(case, RecoveryCaseStatus.ESCALATED)
    else:
        transition(case, RecoveryCaseStatus.PLANNED)

    _record_history(
        session, case, action=action.value, previous_state=previous_state, new_state=case.status, reason=reason
    )
    session.commit()
    return {"already_planned": False, "action": action.value, "reason": reason, "status": case.status}


# ---------------------------------------------------------------------------
# 2. Validate
# ---------------------------------------------------------------------------


def validate_action_step(session: Session, case: RecoveryCase) -> dict:
    if case.status == RecoveryCaseStatus.VALIDATED.value:
        return {
            "already_validated": True,
            "allowed": True,
            "rejection_reason": None,
            "status": case.status,
        }

    if case.status != RecoveryCaseStatus.PLANNED.value:
        return {
            "already_validated": False,
            "allowed": False,
            "rejection_reason": f"Case must be PLANNED before validation (current status: {case.status}).",
            "status": case.status,
        }

    payment = case.payment
    customer = case.customer
    subscription = payment.subscription

    allowed, rejection_reason = validate_safety(case, payment, customer, subscription)

    previous_state = case.status
    case.last_validation_result = "passed" if allowed else "rejected"
    case.last_validation_reason = rejection_reason

    transition(case, RecoveryCaseStatus.VALIDATED if allowed else RecoveryCaseStatus.FAILED)

    reason = rejection_reason or "Action passed safety validation."
    _record_history(
        session,
        case,
        action=case.action,
        previous_state=previous_state,
        new_state=case.status,
        reason=reason,
        validation_result=case.last_validation_result,
    )
    session.commit()
    return {
        "already_validated": False,
        "allowed": allowed,
        "rejection_reason": rejection_reason,
        "status": case.status,
    }


# ---------------------------------------------------------------------------
# 3. Execute (simulated only -- never calls a real payment provider)
# ---------------------------------------------------------------------------


def execute_action(session: Session, case: RecoveryCase) -> dict:
    if case.status in {s.value for s in TERMINAL_STATES}:
        return {
            "already_executed": True,
            "execution_status": case.execution_status,
            "recovered_amount": float(case.recovered_amount or 0),
            "status": case.status,
            "failure_reason": case.execution_failure_reason,
        }

    if case.status != RecoveryCaseStatus.VALIDATED.value:
        return {"error": f"Case must be VALIDATED before execution (current status: {case.status})."}

    previous_state = case.status
    transition(case, RecoveryCaseStatus.EXECUTING)
    _record_history(
        session,
        case,
        action=case.action,
        previous_state=previous_state,
        new_state=case.status,
        reason="Execution started (simulated -- no real payment provider is called).",
    )

    payment = case.payment
    customer = case.customer
    result = simulate_execution(case, payment, customer)

    case.recovery_attempts = (case.recovery_attempts or 0) + 1
    case.execution_status = result["execution_status"]
    case.executed_at = datetime.utcnow()
    case.execution_failure_reason = result["failure_reason"]
    # Defensive clamp: recovered amount must never exceed amount_at_risk.
    recovered = min(result["recovered_amount"], float(case.amount_at_risk))
    case.recovered_amount = recovered

    previous_state = case.status
    transition(case, result["new_status"])

    _record_history(
        session,
        case,
        action=case.action,
        previous_state=previous_state,
        new_state=case.status,
        reason=result["failure_reason"] or "Execution simulated successfully.",
        execution_result=result["execution_status"],
        amount=recovered,
    )
    session.commit()

    return {
        "already_executed": False,
        "execution_status": result["execution_status"],
        "recovered_amount": recovered,
        "status": case.status,
        "failure_reason": result["failure_reason"],
    }


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def get_action_summary(session: Session) -> dict:
    total = session.execute(select(func.count()).select_from(RecoveryCase)).scalar() or 0
    planned = (
        session.execute(select(func.count()).select_from(RecoveryCase).where(RecoveryCase.action.isnot(None))).scalar()
        or 0
    )
    validated = (
        session.execute(
            select(func.count()).select_from(RecoveryCase).where(RecoveryCase.last_validation_result == "passed")
        ).scalar()
        or 0
    )
    executed = (
        session.execute(
            select(func.count()).select_from(RecoveryCase).where(RecoveryCase.executed_at.isnot(None))
        ).scalar()
        or 0
    )
    recovered = (
        session.execute(
            select(func.count()).select_from(RecoveryCase).where(RecoveryCase.status == RecoveryCaseStatus.RECOVERED.value)
        ).scalar()
        or 0
    )
    failed = (
        session.execute(
            select(func.count()).select_from(RecoveryCase).where(RecoveryCase.status == RecoveryCaseStatus.FAILED.value)
        ).scalar()
        or 0
    )
    escalated = (
        session.execute(
            select(func.count()).select_from(RecoveryCase).where(RecoveryCase.status == RecoveryCaseStatus.ESCALATED.value)
        ).scalar()
        or 0
    )
    recovered_revenue = session.execute(select(func.sum(RecoveryCase.recovered_amount))).scalar() or 0

    return {
        "total_opportunities": total,
        "actions_planned": planned,
        "actions_validated": validated,
        "actions_executed": executed,
        "recovered_cases": recovered,
        "failed_cases": failed,
        "escalated_cases": escalated,
        "simulated_recovered_revenue": float(recovered_revenue),
    }
