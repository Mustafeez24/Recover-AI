import enum


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    PAUSED = "paused"


class PaymentStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ABANDONED = "abandoned"


class FailureReason(str, enum.Enum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    TEMPORARY_FAILURE = "temporary_failure"
    BANK_DECLINED = "bank_declined"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    CHECKOUT_ABANDONED = "checkout_abandoned"


class PaymentMethod(str, enum.Enum):
    CARD = "card"
    UPI = "upi"
    NETBANKING = "netbanking"
    WALLET = "wallet"


class RecoveryPriority(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FailureCategory(str, enum.Enum):
    TEMPORARY_FAILURE = "temporary_failure"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    PAYMENT_TIMEOUT = "payment_timeout"
    SUBSCRIPTION_FAILURE = "subscription_failure"
    ABANDONED_CHECKOUT = "abandoned_checkout"
    REPEATED_FAILURE = "repeated_failure"
