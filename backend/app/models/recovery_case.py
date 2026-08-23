from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.enums import FailureCategory, RecoveryCaseStatus, RecoveryPriority


class RecoveryCase(Base):
    """A detected, deterministic revenue-recovery opportunity.

    Created by Phase 3's detection engine (status starts at DETECTED).
    Phase 4's recovery workflow (plan -> validate -> execute) then drives
    it through the rest of the state machine defined in
    `app.recovery.state_machine`. Everything Phase 4 does is simulated
    locally -- no real payment is ever moved.
    """

    __tablename__ = "recovery_cases"

    recovery_case_id = Column(String, primary_key=True)
    payment_id = Column(
        String, ForeignKey("payments.payment_id"), nullable=False, unique=True
    )
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    status = Column(String, nullable=False, default=RecoveryCaseStatus.DETECTED.value)

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

    # --- Phase 4: planning / validation / execution ---
    action = Column(String, nullable=True)
    action_reason = Column(String, nullable=True)
    planned_at = Column(DateTime, nullable=True)

    last_validation_result = Column(String, nullable=True)  # "passed" | "rejected"
    last_validation_reason = Column(String, nullable=True)

    execution_status = Column(String, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    execution_failure_reason = Column(String, nullable=True)
    recovered_amount = Column(Numeric(10, 2), nullable=False, default=0)
    recovery_attempts = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    payment = relationship("Payment", back_populates="recovery_case")
    customer = relationship("Customer", back_populates="recovery_cases")
    history = relationship(
        "RecoveryActionHistory",
        back_populates="recovery_case",
        cascade="all, delete-orphan",
        order_by="RecoveryActionHistory.created_at",
    )

    __table_args__ = (
        Index("ix_recovery_cases_customer_id", "customer_id"),
        Index("ix_recovery_cases_status", "status"),
        Index("ix_recovery_cases_priority", "priority"),
        Index("ix_recovery_cases_failure_category", "failure_category"),
        Index("ix_recovery_cases_amount_at_risk", "amount_at_risk"),
    )
