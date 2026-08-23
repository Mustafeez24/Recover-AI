"""Deterministic recovery-action rules: what to do, whether it's safe to
do, and what simulated outcome it produces. No ML/LLM, no randomness, no
real payment execution anywhere in this module -- everything here is a
plain rule over data already in the database, and "execution" only ever
writes to the local RecoveryCase row.
"""

from app.models.enums import (
    FailureCategory,
    PaymentStatus,
    RecoveryAction,
    RecoveryCaseStatus,
    RecoveryPriority,
    SubscriptionStatus,
)
from app.recovery.rules import MAX_RETRY_CAP, NEUTRAL_HISTORY_RATE, customer_success_rate

# How many automated plan->validate->execute cycles a single case may go
# through (across FAILED -> PLANNED retries) before it's exhausted.
RECOVERY_ATTEMPT_CAP = 3

# Repeated-failure cases at or above this amount are escalated rather than
# handled automatically, regardless of customer history.
HIGH_RISK_ESCALATION_AMOUNT = 5000

# A retry is simulated as successful when the customer's historical
# success rate is at least this high.
RETRY_SUCCESS_RATE_THRESHOLD = 0.5

# Which actions are semantically valid for each failure category. ESCALATE
# is always allowed everywhere as the universal safe fallback. Used both
# by action selection (as a sanity check) and, independently, by the
# safety validator -- the validator does not trust the planner blindly.
ALLOWED_ACTIONS_BY_CATEGORY = {
    FailureCategory.TEMPORARY_FAILURE: {RecoveryAction.RETRY_PAYMENT, RecoveryAction.SCHEDULE_RETRY},
    FailureCategory.PAYMENT_TIMEOUT: {RecoveryAction.RETRY_PAYMENT, RecoveryAction.SCHEDULE_RETRY},
    FailureCategory.INSUFFICIENT_FUNDS: {RecoveryAction.SEND_PAYMENT_REMINDER, RecoveryAction.SCHEDULE_RETRY},
    FailureCategory.ABANDONED_CHECKOUT: {RecoveryAction.SEND_PAYMENT_REMINDER},
    FailureCategory.SUBSCRIPTION_FAILURE: {RecoveryAction.RETRY_PAYMENT, RecoveryAction.REQUEST_PAYMENT_METHOD_UPDATE},
    FailureCategory.REPEATED_FAILURE: {RecoveryAction.REQUEST_PAYMENT_METHOD_UPDATE},
}


# ---------------------------------------------------------------------------
# 1. Action selection
# ---------------------------------------------------------------------------


def select_action(case, payment, customer, subscription):
    """Returns (RecoveryAction, human-readable reason)."""
    if payment.retry_count >= MAX_RETRY_CAP:
        return RecoveryAction.ESCALATE, (
            f"Payment already retried {payment.retry_count} time(s) (limit {MAX_RETRY_CAP}); "
            "escalating for manual review instead of another automated attempt."
        )

    if (case.recovery_attempts or 0) >= RECOVERY_ATTEMPT_CAP:
        return RecoveryAction.ESCALATE, (
            f"{case.recovery_attempts} automated recovery attempt(s) already made "
            f"(limit {RECOVERY_ATTEMPT_CAP}); escalating for manual review."
        )

    category = case.failure_category

    if category == FailureCategory.ABANDONED_CHECKOUT:
        return RecoveryAction.SEND_PAYMENT_REMINDER, "Abandoned checkout: a reminder is the safest first step."

    if category == FailureCategory.TEMPORARY_FAILURE:
        return (
            RecoveryAction.RETRY_PAYMENT,
            "Temporary failure with retries remaining: safe to retry automatically.",
        )

    if category == FailureCategory.PAYMENT_TIMEOUT:
        if payment.retry_count == 0:
            return RecoveryAction.RETRY_PAYMENT, "Timeout on the first attempt: safe to retry immediately."
        return (
            RecoveryAction.SCHEDULE_RETRY,
            "Timeout after a prior attempt: schedule a delayed retry rather than retrying immediately again.",
        )

    if category == FailureCategory.INSUFFICIENT_FUNDS:
        if case.priority == RecoveryPriority.HIGH:
            return (
                RecoveryAction.SCHEDULE_RETRY,
                "High-value insufficient-funds case: schedule a retry to allow time for funds to become available.",
            )
        return (
            RecoveryAction.SEND_PAYMENT_REMINDER,
            "Insufficient funds: send a reminder rather than retrying immediately.",
        )

    if category == FailureCategory.SUBSCRIPTION_FAILURE:
        if subscription is not None and subscription.status == SubscriptionStatus.CANCELED:
            return RecoveryAction.ESCALATE, "Subscription is already canceled: escalate rather than auto-retry."
        if payment.retry_count == 0:
            return RecoveryAction.RETRY_PAYMENT, "Subscription payment failed once: safe to retry automatically."
        return (
            RecoveryAction.REQUEST_PAYMENT_METHOD_UPDATE,
            "Subscription payment already retried without success: request an updated payment method.",
        )

    if category == FailureCategory.REPEATED_FAILURE:
        amount = float(case.amount_at_risk)
        success_rate = customer_success_rate(customer)
        if amount >= HIGH_RISK_ESCALATION_AMOUNT or success_rate < NEUTRAL_HISTORY_RATE:
            why = []
            if amount >= HIGH_RISK_ESCALATION_AMOUNT:
                why.append(f"high-value case (₹{amount:.2f})")
            if success_rate < NEUTRAL_HISTORY_RATE:
                why.append(f"weak customer payment history ({success_rate:.0%} success rate)")
            return (
                RecoveryAction.ESCALATE,
                f"Repeated failures on a {' and '.join(why)}: unsafe to automate further.",
            )
        return (
            RecoveryAction.REQUEST_PAYMENT_METHOD_UPDATE,
            f"Repeated failures but reasonable customer history ({success_rate:.0%} success rate): "
            "request an updated payment method.",
        )

    # Every eligible case is classified into one of the six categories
    # above by Phase 3; this is a defensive fallback only.
    return RecoveryAction.ESCALATE, "Unrecognized failure category: escalating for manual review."


# ---------------------------------------------------------------------------
# 2. Safety validation (runs before execution)
# ---------------------------------------------------------------------------


def validate_safety(case, payment, customer, subscription):
    """Returns (allowed: bool, rejection_reason: str | None). Never raises;
    the caller decides what a rejection means for the case's state."""
    if payment is None or customer is None or case.action is None:
        return False, "Required payment/recovery information is missing."

    if case.status in {s.value for s in (RecoveryCaseStatus.RECOVERED, RecoveryCaseStatus.EXHAUSTED, RecoveryCaseStatus.ESCALATED)}:
        return False, f"Recovery case is already {case.status}; no further action is allowed."

    if payment.payment_status == PaymentStatus.SUCCESS:
        return False, "Payment already succeeded; rejecting the planned action."

    try:
        action = RecoveryAction(case.action)
    except ValueError:
        return False, f"Unknown action '{case.action}'."

    if action in (RecoveryAction.RETRY_PAYMENT, RecoveryAction.SCHEDULE_RETRY) and payment.retry_count >= MAX_RETRY_CAP:
        return False, f"Retry limit reached ({payment.retry_count} >= {MAX_RETRY_CAP}); this action is no longer allowed."

    if (
        action in (RecoveryAction.RETRY_PAYMENT, RecoveryAction.SCHEDULE_RETRY)
        and subscription is not None
        and subscription.status == SubscriptionStatus.CANCELED
    ):
        return False, "Subscription is canceled; retrying is not appropriate."

    if action != RecoveryAction.ESCALATE:
        allowed_for_category = ALLOWED_ACTIONS_BY_CATEGORY.get(case.failure_category, set())
        if action not in allowed_for_category:
            return False, f"{action.value} is not an allowed action for {case.failure_category.value} cases."

    return True, None


# ---------------------------------------------------------------------------
# 3. Simulated execution
# ---------------------------------------------------------------------------


def simulate_execution(case, payment, customer):
    """Deterministically simulate carrying out `case.action` -- no Razorpay
    call, no randomness. Returns a dict with execution_status, new_status
    (a RecoveryCaseStatus), recovered_amount, and failure_reason."""
    action = RecoveryAction(case.action)
    amount = float(case.amount_at_risk)

    if action == RecoveryAction.RETRY_PAYMENT:
        success_rate = customer_success_rate(customer)
        if success_rate >= RETRY_SUCCESS_RATE_THRESHOLD:
            return {
                "execution_status": "success",
                "new_status": RecoveryCaseStatus.RECOVERED,
                "recovered_amount": amount,
                "failure_reason": None,
            }
        return {
            "execution_status": "failed",
            "new_status": RecoveryCaseStatus.FAILED,
            "recovered_amount": 0.0,
            "failure_reason": (
                f"Retry simulated as unsuccessful: customer success rate "
                f"({success_rate:.0%}) is below the {RETRY_SUCCESS_RATE_THRESHOLD:.0%} threshold."
            ),
        }

    if action == RecoveryAction.SCHEDULE_RETRY:
        return {
            "execution_status": "scheduled",
            "new_status": RecoveryCaseStatus.FAILED,
            "recovered_amount": 0.0,
            "failure_reason": "Retry scheduled for later; not yet attempted.",
        }

    if action == RecoveryAction.SEND_PAYMENT_REMINDER:
        return {
            "execution_status": "pending_customer_action",
            "new_status": RecoveryCaseStatus.FAILED,
            "recovered_amount": 0.0,
            "failure_reason": "Reminder sent; awaiting customer action.",
        }

    if action == RecoveryAction.REQUEST_PAYMENT_METHOD_UPDATE:
        return {
            "execution_status": "action_required",
            "new_status": RecoveryCaseStatus.FAILED,
            "recovered_amount": 0.0,
            "failure_reason": "Payment method update requested; awaiting customer update.",
        }

    if action == RecoveryAction.ESCALATE:
        return {
            "execution_status": "escalated",
            "new_status": RecoveryCaseStatus.ESCALATED,
            "recovered_amount": 0.0,
            "failure_reason": None,
        }

    raise ValueError(f"Unknown action: {action}")
