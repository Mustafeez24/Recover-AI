"""Deterministic revenue-leakage detection rules.

No ML or LLM is involved anywhere in this module -- every decision is a
plain, explainable rule over fields already in the database (payment
status/failure reason/amount/retry_count, customer payment history and
lifetime value, subscription status). Phase 3 only identifies and
prioritizes recovery opportunities; it never decides or executes a
recovery action -- that is Phase 4's job. `recommended_next_step` here is
a suggestion label only, nothing is actually attempted.
"""

from app.models.enums import (
    FailureCategory,
    FailureReason,
    PaymentStatus,
    RecoveryPriority,
    SubscriptionStatus,
)

# Retry attempts at or above this count are treated as "repeated failure"
# and escalated (still eligible, but flagged for closer attention).
REPEATED_FAILURE_THRESHOLD = 2

# Retry attempts at or above this count are considered exhausted: further
# automated recovery is not attempted for that payment.
MAX_RETRY_CAP = 4

# Amount thresholds (INR) used for the priority score.
HIGH_VALUE_AMOUNT = 2000
MID_VALUE_AMOUNT = 500

# Customer success-rate thresholds used for the priority score.
STRONG_HISTORY_RATE = 0.7
NEUTRAL_HISTORY_RATE = 0.4

RECOMMENDED_NEXT_STEP = {
    FailureCategory.ABANDONED_CHECKOUT: "send_checkout_reminder",
    FailureCategory.PAYMENT_TIMEOUT: "retry_payment",
    FailureCategory.TEMPORARY_FAILURE: "retry_payment",
    FailureCategory.INSUFFICIENT_FUNDS: "send_payment_reminder",
    FailureCategory.SUBSCRIPTION_FAILURE: "retry_subscription_payment",
    FailureCategory.REPEATED_FAILURE: "escalate_to_manual_review",
}


def classify_failure_category(payment) -> FailureCategory:
    """Assign exactly one category, checked in this priority order."""
    if payment.payment_status == PaymentStatus.ABANDONED:
        return FailureCategory.ABANDONED_CHECKOUT
    if payment.payment_status == PaymentStatus.TIMEOUT:
        return FailureCategory.PAYMENT_TIMEOUT
    if payment.retry_count >= REPEATED_FAILURE_THRESHOLD:
        return FailureCategory.REPEATED_FAILURE
    if payment.subscription_id is not None:
        return FailureCategory.SUBSCRIPTION_FAILURE
    if payment.failure_reason == FailureReason.INSUFFICIENT_FUNDS:
        return FailureCategory.INSUFFICIENT_FUNDS
    return FailureCategory.TEMPORARY_FAILURE


def customer_success_rate(customer) -> float:
    total = customer.total_successful_payments + customer.total_failed_payments
    if total == 0:
        return 0.5  # no history yet: neutral, neither strong nor weak
    return customer.total_successful_payments / total


def evaluate_eligibility(payment, subscription):
    """Returns (eligible, reason_if_not_eligible)."""
    if payment.payment_status == PaymentStatus.SUCCESS:
        return False, "Payment already succeeded; there is nothing to recover."
    if payment.retry_count >= MAX_RETRY_CAP:
        return False, (
            f"Retry attempts exhausted ({payment.retry_count} >= {MAX_RETRY_CAP}); "
            "further automated recovery is not attempted."
        )
    if subscription is not None and subscription.status == SubscriptionStatus.CANCELED:
        return False, "Subscription is already canceled; recovery is not applicable."
    return True, None


def calculate_priority(payment, customer, category: FailureCategory):
    """Deterministic point score -> HIGH/MEDIUM/LOW, plus the human-readable
    factors that produced it (used to build the audit-trail reason string).
    """
    score = 0
    factors = []

    amount = float(payment.amount)
    if amount >= HIGH_VALUE_AMOUNT:
        score += 2
        factors.append(f"high-value payment (₹{amount:.2f})")
    elif amount >= MID_VALUE_AMOUNT:
        score += 1
        factors.append(f"mid-value payment (₹{amount:.2f})")
    else:
        factors.append(f"low-value payment (₹{amount:.2f})")

    rate = customer_success_rate(customer)
    if rate >= STRONG_HISTORY_RATE:
        score += 2
        factors.append(f"strong customer payment history ({rate:.0%} success rate)")
    elif rate >= NEUTRAL_HISTORY_RATE:
        score += 1
        factors.append(f"moderate customer payment history ({rate:.0%} success rate)")
    else:
        factors.append(f"weak customer payment history ({rate:.0%} success rate)")

    score += 1
    factors.append(f"{category.value.replace('_', ' ')} is typically actionable")

    if payment.retry_count == 0:
        score += 1
        factors.append("no retry attempted yet, full recovery window available")
    elif payment.retry_count >= 3:
        score -= 1
        factors.append(f"already retried {payment.retry_count} time(s), narrowing the recovery window")

    if score >= 5:
        priority = RecoveryPriority.HIGH
    elif score >= 3:
        priority = RecoveryPriority.MEDIUM
    else:
        priority = RecoveryPriority.LOW

    return priority, factors


def analyze_payment(payment, customer, subscription) -> dict:
    """Run every deterministic rule for one payment and return the full decision.

    Example (eligible case):
        {
          "eligible": true,
          "priority": "high",
          "amount_at_risk": 4999.0,
          "detection_reason": "HIGH priority temporary failure: high-value
            payment (₹4999.00); strong customer payment history (85%
            success rate); temporary failure is typically actionable; no
            retry attempted yet, full recovery window available.",
          "customer_value": 52340.0,
          "failure_category": "temporary_failure",
          "recommended_next_step": "retry_payment"
        }
    """
    eligible, ineligible_reason = evaluate_eligibility(payment, subscription)
    customer_value = float(customer.lifetime_value)

    if not eligible:
        return {
            "eligible": False,
            "priority": None,
            "amount_at_risk": None,
            "detection_reason": ineligible_reason,
            "customer_value": customer_value,
            "failure_category": None,
            "recommended_next_step": None,
        }

    category = classify_failure_category(payment)
    priority, factors = calculate_priority(payment, customer, category)
    amount_at_risk = round(float(payment.amount), 2)

    reason = (
        f"{priority.value.upper()} priority {category.value.replace('_', ' ')}: "
        + "; ".join(factors)
        + "."
    )

    return {
        "eligible": True,
        "priority": priority,
        "amount_at_risk": amount_at_risk,
        "detection_reason": reason,
        "customer_value": customer_value,
        "failure_category": category,
        "recommended_next_step": RECOMMENDED_NEXT_STEP[category],
    }
