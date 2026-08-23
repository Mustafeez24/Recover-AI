from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Index, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True)
    customer_since = Column(Date, nullable=False)
    total_successful_payments = Column(Integer, nullable=False, default=0)
    total_failed_payments = Column(Integer, nullable=False, default=0)
    lifetime_value = Column(Numeric(12, 2), nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    payments = relationship(
        "Payment", back_populates="customer", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "Subscription", back_populates="customer", cascade="all, delete-orphan"
    )
    recovery_cases = relationship(
        "RecoveryCase", back_populates="customer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_customers_total_failed_payments", "total_failed_payments"),
    )
