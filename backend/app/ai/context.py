"""Builds a compact, controlled context for the AI -- only what's useful
for a recovery recommendation, nothing else. No names, emails, or other
PII (the schema never stores any), no full database dumps, no raw audit
history. Kept small deliberately: the local model is only 3B parameters.
"""

from app.recovery.rules import customer_success_rate


def build_context(case) -> dict:
    payment = case.payment
    customer = case.customer
    subscription = payment.subscription

    return {
        "payment_amount": float(payment.amount),
        "currency": payment.currency,
        "payment_status": payment.payment_status.value,
        "failure_reason": payment.failure_reason.value if payment.failure_reason else None,
        "failure_category": case.failure_category.value,
        "retry_count": payment.retry_count,
        "customer_total_successful_payments": customer.total_successful_payments,
        "customer_total_failed_payments": customer.total_failed_payments,
        "customer_success_rate": round(customer_success_rate(customer), 2),
        "customer_lifetime_value": float(customer.lifetime_value),
        "subscription_status": subscription.status.value if subscription else None,
        "recovery_priority": case.priority.value,
        "amount_at_risk": float(case.amount_at_risk),
        "recovery_attempts_so_far": case.recovery_attempts or 0,
        "deterministic_recommended_action": case.recommended_next_step,
        "previously_planned_action": case.action,
    }
