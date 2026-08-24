from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class AIRecommendation(Base):
    """One row per AI analysis run against a RecoveryCase (Phase 5).

    Purely advisory: the AI never executes anything. Every call is
    recorded here -- successful or not -- alongside the deterministic
    Phase 4 action it was compared against and the outcome of running it
    through the same safety validator real actions go through. This is
    what lets AI-vs-deterministic agreement be measured, and lets a
    rejected/failed AI call always fall back to the deterministic action
    without losing the audit trail of what the AI said.
    """

    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recovery_case_id = Column(
        String, ForeignKey("recovery_cases.recovery_case_id"), nullable=False
    )

    ai_recommended_action = Column(String, nullable=True)
    ai_confidence = Column(Float, nullable=True)
    ai_reason = Column(String, nullable=True)
    ai_risk_level = Column(String, nullable=True)
    ai_customer_context = Column(String, nullable=True)
    ai_alternative_action = Column(String, nullable=True)
    ai_status = Column(String, nullable=False)  # ok | unavailable | timeout | provider_error | invalid_json | invalid_schema
    ai_model = Column(String, nullable=False)
    ai_generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    deterministic_action = Column(String, nullable=False)
    safety_validation_result = Column(String, nullable=True)  # passed | rejected | null (AI call didn't succeed)
    safety_rejection_reason = Column(String, nullable=True)
    agreement = Column(Boolean, nullable=True)  # null when AI call didn't succeed
    fallback_used = Column(Boolean, nullable=False, default=True)
    effective_action = Column(String, nullable=False)

    recovery_case = relationship("RecoveryCase", back_populates="ai_recommendations")

    __table_args__ = (
        Index("ix_ai_recommendations_case_id", "recovery_case_id"),
        Index("ix_ai_recommendations_status", "ai_status"),
        Index("ix_ai_recommendations_generated_at", "ai_generated_at"),
    )
