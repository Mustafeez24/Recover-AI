from datetime import date, datetime

from app.models import (
    Customer,
    FailureCategory,
    Payment,
    PaymentMethod,
    PaymentStatus,
    RecoveryAction,
    RecoveryActionHistory,
    RecoveryCase,
    RecoveryCaseStatus,
    RecoveryPriority,
)
from app.recovery.action_rules import RECOVERY_ATTEMPT_CAP
from app.recovery.rules import MAX_RETRY_CAP
from app.recovery.workflow import execute_action, get_action_summary, plan_action, validate_action_step


def _add_customer(db, customer_id="cus_wf", success=8, failed=2, lifetime_value=5000.0):
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


def _add_recovery_case(
    db,
    case_id,
    payment_id,
    customer_id,
    failure_category=FailureCategory.TEMPORARY_FAILURE,
    priority=RecoveryPriority.MEDIUM,
    amount_at_risk=1000.0,
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
# Full plan -> validate -> execute flow
# ---------------------------------------------------------------------------


def test_full_flow_recovers_case(db_session):
    customer = _add_customer(db_session, success=9, failed=1)  # 90% success rate
    payment = _add_payment(db_session, "pay_wf1", customer.customer_id, amount=1000.0)
    case = _add_recovery_case(db_session, "rec_wf1", payment.payment_id, customer.customer_id, amount_at_risk=1000.0)

    plan_result = plan_action(db_session, case)
    assert plan_result["action"] == RecoveryAction.RETRY_PAYMENT.value
    assert case.status == RecoveryCaseStatus.PLANNED.value

    validate_result = validate_action_step(db_session, case)
    assert validate_result["allowed"] is True
    assert case.status == RecoveryCaseStatus.VALIDATED.value

    execute_result = execute_action(db_session, case)
    assert execute_result["execution_status"] == "success"
    assert execute_result["recovered_amount"] == 1000.0
    assert case.status == RecoveryCaseStatus.RECOVERED.value
    assert float(case.recovered_amount) == 1000.0


def test_full_flow_failed_execution(db_session):
    customer = _add_customer(db_session, success=1, failed=9)  # 10% success rate
    payment = _add_payment(db_session, "pay_wf2", customer.customer_id, amount=800.0)
    case = _add_recovery_case(db_session, "rec_wf2", payment.payment_id, customer.customer_id, amount_at_risk=800.0)

    plan_action(db_session, case)
    validate_action_step(db_session, case)
    result = execute_action(db_session, case)

    assert result["execution_status"] == "failed"
    assert result["recovered_amount"] == 0.0
    assert case.status == RecoveryCaseStatus.FAILED.value


def test_full_flow_escalation(db_session):
    customer = _add_customer(db_session, success=1, failed=9)
    payment = _add_payment(db_session, "pay_wf3", customer.customer_id, amount=6000.0, retry_count=2)
    case = _add_recovery_case(
        db_session,
        "rec_wf3",
        payment.payment_id,
        customer.customer_id,
        failure_category=FailureCategory.REPEATED_FAILURE,
        amount_at_risk=6000.0,
    )

    plan_action(db_session, case)
    assert case.action == RecoveryAction.ESCALATE.value
    assert case.status == RecoveryCaseStatus.PLANNED.value

    validate_action_step(db_session, case)
    assert case.status == RecoveryCaseStatus.VALIDATED.value

    result = execute_action(db_session, case)
    assert result["execution_status"] == "escalated"
    assert case.status == RecoveryCaseStatus.ESCALATED.value


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_plan_is_idempotent(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_wf4", customer.customer_id)
    case = _add_recovery_case(db_session, "rec_wf4", payment.payment_id, customer.customer_id)

    first = plan_action(db_session, case)
    assert first["already_planned"] is False

    second = plan_action(db_session, case)
    assert second["already_planned"] is True
    assert second["action"] == first["action"]

    history_count = (
        db_session.query(RecoveryActionHistory).filter_by(recovery_case_id=case.recovery_case_id).count()
    )
    assert history_count == 1


def test_execute_is_idempotent_no_double_counted_revenue(db_session):
    customer = _add_customer(db_session, success=9, failed=1)
    payment = _add_payment(db_session, "pay_wf5", customer.customer_id, amount=500.0)
    case = _add_recovery_case(db_session, "rec_wf5", payment.payment_id, customer.customer_id, amount_at_risk=500.0)

    plan_action(db_session, case)
    validate_action_step(db_session, case)
    first = execute_action(db_session, case)
    second = execute_action(db_session, case)

    assert first["already_executed"] is False
    assert second["already_executed"] is True
    assert second["recovered_amount"] == first["recovered_amount"] == 500.0
    assert float(case.recovered_amount) == 500.0  # not doubled


def test_execute_before_validation_returns_error(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_wf6", customer.customer_id)
    case = _add_recovery_case(db_session, "rec_wf6", payment.payment_id, customer.customer_id)

    plan_action(db_session, case)  # now PLANNED, not VALIDATED
    result = execute_action(db_session, case)
    assert "error" in result
    assert case.status == RecoveryCaseStatus.PLANNED.value


# ---------------------------------------------------------------------------
# Validation rejection, re-planning, exhaustion
# ---------------------------------------------------------------------------


def test_validate_rejects_when_payment_succeeds_after_planning(db_session):
    customer = _add_customer(db_session)
    payment = _add_payment(db_session, "pay_wf7", customer.customer_id)
    case = _add_recovery_case(db_session, "rec_wf7", payment.payment_id, customer.customer_id)

    plan_action(db_session, case)

    # The payment succeeded through some other path before we validated.
    payment.payment_status = PaymentStatus.SUCCESS
    db_session.commit()

    result = validate_action_step(db_session, case)
    assert result["allowed"] is False
    assert "already succeeded" in result["rejection_reason"]
    assert case.status == RecoveryCaseStatus.FAILED.value


def test_failed_case_can_be_replanned(db_session):
    customer = _add_customer(db_session, success=1, failed=9)  # weak history: retry will fail
    payment = _add_payment(db_session, "pay_wf8", customer.customer_id, amount=300.0)
    case = _add_recovery_case(db_session, "rec_wf8", payment.payment_id, customer.customer_id, amount_at_risk=300.0)

    plan_action(db_session, case)
    validate_action_step(db_session, case)
    execute_action(db_session, case)
    assert case.status == RecoveryCaseStatus.FAILED.value
    assert case.recovery_attempts == 1

    replan = plan_action(db_session, case)
    assert replan["already_planned"] is False
    assert case.status == RecoveryCaseStatus.PLANNED.value


def test_case_becomes_exhausted_after_max_recovery_attempts(db_session):
    customer = _add_customer(db_session, success=1, failed=9)  # retries always fail
    payment = _add_payment(db_session, "pay_wf9", customer.customer_id, amount=200.0)
    case = _add_recovery_case(db_session, "rec_wf9", payment.payment_id, customer.customer_id, amount_at_risk=200.0)

    for _ in range(RECOVERY_ATTEMPT_CAP):
        plan_action(db_session, case)
        validate_action_step(db_session, case)
        execute_action(db_session, case)
        assert case.status == RecoveryCaseStatus.FAILED.value

    result = plan_action(db_session, case)
    assert case.status == RecoveryCaseStatus.EXHAUSTED.value
    assert result["already_planned"] is False


def test_failed_case_escalates_on_replan_when_retry_limit_reached(db_session):
    customer = _add_customer(db_session, success=1, failed=9)
    payment = _add_payment(db_session, "pay_wf10", customer.customer_id, amount=300.0, retry_count=0)
    case = _add_recovery_case(db_session, "rec_wf10", payment.payment_id, customer.customer_id, amount_at_risk=300.0)

    plan_action(db_session, case)
    validate_action_step(db_session, case)
    execute_action(db_session, case)
    assert case.status == RecoveryCaseStatus.FAILED.value

    payment.retry_count = MAX_RETRY_CAP
    db_session.commit()

    result = plan_action(db_session, case)
    assert case.status == RecoveryCaseStatus.ESCALATED.value
    assert result["action"] == RecoveryAction.ESCALATE.value


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


def test_audit_history_is_recorded_for_full_flow(db_session):
    customer = _add_customer(db_session, success=9, failed=1)
    payment = _add_payment(db_session, "pay_wf11", customer.customer_id, amount=600.0)
    case = _add_recovery_case(db_session, "rec_wf11", payment.payment_id, customer.customer_id, amount_at_risk=600.0)

    plan_action(db_session, case)
    validate_action_step(db_session, case)
    execute_action(db_session, case)

    history = (
        db_session.query(RecoveryActionHistory)
        .filter_by(recovery_case_id=case.recovery_case_id)
        .order_by(RecoveryActionHistory.created_at, RecoveryActionHistory.id)
        .all()
    )
    assert len(history) == 4  # plan, validate, executing-start, executing-outcome
    assert history[0].new_state == RecoveryCaseStatus.PLANNED.value
    assert history[1].new_state == RecoveryCaseStatus.VALIDATED.value
    assert history[1].validation_result == "passed"
    assert history[2].new_state == RecoveryCaseStatus.EXECUTING.value
    assert history[3].new_state == RecoveryCaseStatus.RECOVERED.value
    assert history[3].execution_result == "success"
    assert float(history[3].amount) == 600.0
    for h in history:
        assert h.recovery_case_id == case.recovery_case_id
        assert h.created_at is not None


# ---------------------------------------------------------------------------
# Summary / empty dataset
# ---------------------------------------------------------------------------


def test_action_summary_empty_dataset(db_session):
    summary = get_action_summary(db_session)
    assert summary == {
        "total_opportunities": 0,
        "actions_planned": 0,
        "actions_validated": 0,
        "actions_executed": 0,
        "recovered_cases": 0,
        "failed_cases": 0,
        "escalated_cases": 0,
        "simulated_recovered_revenue": 0.0,
    }


def test_action_summary_reflects_processed_cases(db_session):
    customer = _add_customer(db_session, success=9, failed=1)
    payment = _add_payment(db_session, "pay_wf12", customer.customer_id, amount=400.0)
    case = _add_recovery_case(db_session, "rec_wf12", payment.payment_id, customer.customer_id, amount_at_risk=400.0)

    plan_action(db_session, case)
    validate_action_step(db_session, case)
    execute_action(db_session, case)

    summary = get_action_summary(db_session)
    assert summary["total_opportunities"] == 1
    assert summary["actions_planned"] == 1
    assert summary["actions_validated"] == 1
    assert summary["actions_executed"] == 1
    assert summary["recovered_cases"] == 1
    assert summary["simulated_recovered_revenue"] == 400.0
