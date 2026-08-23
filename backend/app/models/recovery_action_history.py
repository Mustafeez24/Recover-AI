from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class RecoveryActionHistory(Base):
    """Append-only audit trail: one row per state transition a recovery
    case goes through (planning, validation, execution). Exists so the
    whole recovery workflow stays explainable and auditable end to end.
    """

    __tablename__ = "recovery_action_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recovery_case_id = Column(
        String, ForeignKey("recovery_cases.recovery_case_id"), nullable=False
    )
    action = Column(String, nullable=True)
    previous_state = Column(String, nullable=False)
    new_state = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    validation_result = Column(String, nullable=True)  # "passed" | "rejected" | null
    execution_result = Column(String, nullable=True)  # e.g. "success" | "failed" | null
    amount = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    recovery_case = relationship("RecoveryCase", back_populates="history")

    __table_args__ = (
        Index("ix_recovery_action_history_case_id", "recovery_case_id"),
        Index("ix_recovery_action_history_created_at", "created_at"),
    )
