from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.enums import FailureReason, PaymentMethod, PaymentStatus


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    subscription_id = Column(
        String, ForeignKey("subscriptions.subscription_id"), nullable=True
    )
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    payment_status = Column(
        SAEnum(PaymentStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    failure_reason = Column(
        SAEnum(FailureReason, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    payment_method = Column(
        SAEnum(PaymentMethod, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    created_at = Column(DateTime, nullable=False)
    retry_count = Column(Integer, nullable=False, default=0)

    customer = relationship("Customer", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    recovery_case = relationship(
        "RecoveryCase", back_populates="payment", uselist=False
    )

    __table_args__ = (
        Index("ix_payments_customer_id", "customer_id"),
        Index("ix_payments_subscription_id", "subscription_id"),
        Index("ix_payments_payment_status", "payment_status"),
        Index("ix_payments_created_at", "created_at"),
        Index("ix_payments_customer_status", "customer_id", "payment_status"),
        Index("ix_payments_subscription_status", "subscription_id", "payment_status"),
    )
