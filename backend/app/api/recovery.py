from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import FailureCategory, RecoveryCase, RecoveryPriority
from app.recovery.engine import get_summary, run_detection
from app.recovery.workflow import execute_action, get_action_summary, plan_action, validate_action_step

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


def _case_to_dict(case: RecoveryCase) -> dict:
    return {
        "recovery_case_id": case.recovery_case_id,
        "payment_id": case.payment_id,
        "customer_id": case.customer_id,
        "status": case.status,
        "priority": case.priority.value,
        "amount_at_risk": float(case.amount_at_risk),
        "customer_value": float(case.customer_value),
        "failure_category": case.failure_category.value,
        "detection_reason": case.detection_reason,
        "recommended_next_step": case.recommended_next_step,
        "created_at": case.created_at.isoformat(),
        "action": case.action,
        "action_reason": case.action_reason,
        "last_validation_result": case.last_validation_result,
        "execution_status": case.execution_status,
        "recovered_amount": float(case.recovered_amount or 0),
        "recovery_attempts": case.recovery_attempts or 0,
    }


@router.post("/detect")
def detect(db: Session = Depends(get_db)):
    """Run the detection engine over every payment and create recovery
    opportunities for newly-eligible ones. Safe to call repeatedly --
    payments that already have a case are skipped, not duplicated."""
    run_result = run_detection(db)
    return {"run": run_result, "summary": get_summary(db)}


@router.get("/opportunities")
def list_opportunities(
    db: Session = Depends(get_db),
    priority: Optional[RecoveryPriority] = None,
    status: Optional[str] = None,
    failure_category: Optional[FailureCategory] = None,
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    stmt = select(RecoveryCase)
    if priority is not None:
        stmt = stmt.where(RecoveryCase.priority == priority)
    if status is not None:
        stmt = stmt.where(RecoveryCase.status == status)
    if failure_category is not None:
        stmt = stmt.where(RecoveryCase.failure_category == failure_category)
    if min_amount is not None:
        stmt = stmt.where(RecoveryCase.amount_at_risk >= min_amount)
    if max_amount is not None:
        stmt = stmt.where(RecoveryCase.amount_at_risk <= max_amount)

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar()

    stmt = stmt.order_by(RecoveryCase.amount_at_risk.desc()).offset(offset).limit(limit)
    cases = db.execute(stmt).scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "opportunities": [_case_to_dict(c) for c in cases],
    }


@router.get("/opportunities/{recovery_case_id}")
def get_opportunity(recovery_case_id: str, db: Session = Depends(get_db)):
    case = db.get(RecoveryCase, recovery_case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery opportunity not found")

    payload = _case_to_dict(case)
    payload["payment"] = {
        "payment_id": case.payment.payment_id,
        "amount": float(case.payment.amount),
        "currency": case.payment.currency,
        "payment_status": case.payment.payment_status.value,
        "failure_reason": case.payment.failure_reason.value if case.payment.failure_reason else None,
        "retry_count": case.payment.retry_count,
        "subscription_id": case.payment.subscription_id,
        "created_at": case.payment.created_at.isoformat(),
    }
    payload["customer"] = {
        "customer_id": case.customer.customer_id,
        "total_successful_payments": case.customer.total_successful_payments,
        "total_failed_payments": case.customer.total_failed_payments,
        "lifetime_value": float(case.customer.lifetime_value),
    }
    return payload


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return get_summary(db)


def _get_case_or_404(db: Session, recovery_case_id: str) -> RecoveryCase:
    case = db.get(RecoveryCase, recovery_case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Recovery opportunity not found")
    return case


@router.post("/opportunities/{recovery_case_id}/plan")
def plan(recovery_case_id: str, db: Session = Depends(get_db)):
    """Select a recovery action for this opportunity. Safe to call
    repeatedly -- an already-planned case is returned as-is."""
    case = _get_case_or_404(db, recovery_case_id)
    return plan_action(db, case)


@router.post("/opportunities/{recovery_case_id}/validate")
def validate(recovery_case_id: str, db: Session = Depends(get_db)):
    """Run the safety validator on the planned action. Never executes
    anything -- only decides whether execution would be allowed."""
    case = _get_case_or_404(db, recovery_case_id)
    return validate_action_step(db, case)


@router.post("/opportunities/{recovery_case_id}/execute")
def execute(recovery_case_id: str, db: Session = Depends(get_db)):
    """Simulate carrying out the validated action locally. Never calls a
    real payment provider, and never moves real money. Safe to call
    repeatedly -- a terminal case's existing result is returned, not
    double-counted."""
    case = _get_case_or_404(db, recovery_case_id)
    result = execute_action(db, case)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/opportunities/{recovery_case_id}/history")
def history(recovery_case_id: str, db: Session = Depends(get_db)):
    case = _get_case_or_404(db, recovery_case_id)
    return {
        "recovery_case_id": case.recovery_case_id,
        "current_status": case.status,
        "history": [
            {
                "action": h.action,
                "previous_state": h.previous_state,
                "new_state": h.new_state,
                "reason": h.reason,
                "validation_result": h.validation_result,
                "execution_result": h.execution_result,
                "amount": float(h.amount) if h.amount is not None else None,
                "created_at": h.created_at.isoformat(),
            }
            for h in case.history
        ],
    }


@router.get("/action-summary")
def action_summary(db: Session = Depends(get_db)):
    return get_action_summary(db)
