from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.enums import SubscriptionStatus


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscription_id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("customers.customer_id"), nullable=False)
    plan = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(
        SAEnum(SubscriptionStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    next_payment_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")

    __table_args__ = (
        Index("ix_subscriptions_customer_id", "customer_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_next_payment_date", "next_payment_date"),
    )
