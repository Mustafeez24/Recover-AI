from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.enums import FailureCategory, RecoveryPriority


class RecoveryCase(Base):
    """A detected, deterministic revenue-recovery opportunity (Phase 3).

    Created only for payments the detection engine judged eligible; holds
    everything Phase 4's recovery workflow needs to act on the case. Phase 3
    never decides or executes the recovery action itself -- `status` stays
    "open" here, and `recommended_next_step` is a suggestion label only.
    """

    __tablename__ = "recovery_cases"

    recovery_case_id = Column(String, primary_key=True)
    payment_id = Column(
        String, ForeignKey("payments.payment_id"), nullable=False, unique=True
    )
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    status = Column(String, nullable=False, default="open")

    priority = Column(
        SAEnum(RecoveryPriority, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    amount_at_risk = Column(Numeric(10, 2), nullable=False)
    customer_value = Column(Numeric(12, 2), nullable=False)
    failure_category = Column(
        SAEnum(FailureCategory, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    detection_reason = Column(String, nullable=False)
    recommended_next_step = Column(String, nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    payment = relationship("Payment", back_populates="recovery_case")
    customer = relationship("Customer", back_populates="recovery_cases")

    __table_args__ = (
        Index("ix_recovery_cases_customer_id", "customer_id"),
        Index("ix_recovery_cases_status", "status"),
        Index("ix_recovery_cases_priority", "priority"),
        Index("ix_recovery_cases_failure_category", "failure_category"),
        Index("ix_recovery_cases_amount_at_risk", "amount_at_risk"),
    )
