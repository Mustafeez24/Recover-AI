from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class RecoveryCase(Base):
    """Schema placeholder for the Phase 3+ recovery engine.

    No recovery logic exists yet; Phase 2 only defines the table so
    later phases can attach recovery cases to failed/timed-out payments.
    """

    __tablename__ = "recovery_cases"

    recovery_case_id = Column(String, primary_key=True)
    payment_id = Column(
        String, ForeignKey("payments.payment_id"), nullable=False, unique=True
    )
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    status = Column(String, nullable=False, default="open")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    payment = relationship("Payment", back_populates="recovery_case")
    customer = relationship("Customer", back_populates="recovery_cases")

    __table_args__ = (
        Index("ix_recovery_cases_customer_id", "customer_id"),
        Index("ix_recovery_cases_status", "status"),
    )
