"""Detection run orchestration and live summary metrics.

`run_detection` is idempotent: it looks up which payments already have a
RecoveryCase (by payment_id, which is unique on the table) before creating
anything, so running it repeatedly never creates duplicates. `get_summary`
computes current-state metrics straight from the database, independent of
when detection last ran.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Payment, PaymentStatus, RecoveryCase, RecoveryPriority
from app.recovery.rules import analyze_payment


def run_detection(session: Session) -> dict:
    existing_payment_ids = {
        row[0] for row in session.execute(select(RecoveryCase.payment_id)).all()
    }

    payments = (
        session.execute(
            select(Payment).options(
                selectinload(Payment.customer), selectinload(Payment.subscription)
            )
        )
        .scalars()
        .all()
    )

    total_payments_analyzed = 0
    failed_payments_analyzed = 0
    opportunities_created = 0
    duplicates_skipped = 0
    ineligible_skipped = 0
    new_cases = []

    for payment in payments:
        total_payments_analyzed += 1
        is_failure_type = payment.payment_status != PaymentStatus.SUCCESS
        if is_failure_type:
            failed_payments_analyzed += 1

        if payment.payment_id in existing_payment_ids:
            if is_failure_type:
                duplicates_skipped += 1
            continue

        result = analyze_payment(payment, payment.customer, payment.subscription)

        if not result["eligible"]:
            if is_failure_type:
                ineligible_skipped += 1
            continue

        new_cases.append(
            {
                "recovery_case_id": f"rec_{payment.payment_id}",
                "payment_id": payment.payment_id,
                "customer_id": payment.customer_id,
                "status": "open",
                "priority": result["priority"],
                "amount_at_risk": result["amount_at_risk"],
                "customer_value": result["customer_value"],
                "failure_category": result["failure_category"],
                "detection_reason": result["detection_reason"],
                "recommended_next_step": result["recommended_next_step"],
                "created_at": datetime.utcnow(),
            }
        )
        opportunities_created += 1

    if new_cases:
        session.bulk_insert_mappings(RecoveryCase, new_cases)
        session.commit()

    return {
        "payments_scanned": total_payments_analyzed,
        "failed_payments_scanned": failed_payments_analyzed,
        "opportunities_created": opportunities_created,
        "duplicates_skipped": duplicates_skipped,
        "ineligible_skipped": ineligible_skipped,
    }


def get_summary(session: Session) -> dict:
    total_payments = session.execute(select(func.count()).select_from(Payment)).scalar() or 0
    failed_payments = (
        session.execute(
            select(func.count())
            .select_from(Payment)
            .where(Payment.payment_status != PaymentStatus.SUCCESS)
        ).scalar()
        or 0
    )
    total_opportunities = session.execute(select(func.count()).select_from(RecoveryCase)).scalar() or 0
    total_at_risk = session.execute(select(func.sum(RecoveryCase.amount_at_risk))).scalar() or 0

    priority_counts = {p.value: 0 for p in RecoveryPriority}
    for priority, count in session.execute(
        select(RecoveryCase.priority, func.count()).group_by(RecoveryCase.priority)
    ).all():
        priority_counts[priority.value] = count

    return {
        "total_payments_analyzed": total_payments,
        "failed_payments_analyzed": failed_payments,
        "recovery_opportunities": total_opportunities,
        "total_revenue_at_risk": float(total_at_risk),
        "high_priority_opportunities": priority_counts["high"],
        "medium_priority_opportunities": priority_counts["medium"],
        "low_priority_opportunities": priority_counts["low"],
        # Non-success payments that were evaluated and correctly excluded
        # (already-succeeded payments are not counted here at all).
        "non_recoverable_payments": failed_payments - total_opportunities,
    }
