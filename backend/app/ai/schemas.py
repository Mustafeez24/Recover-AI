"""Structured, validated shape of an AI recommendation. This is the only
contract the AI's raw text has to satisfy -- anything that doesn't
validate is rejected safely (see app.ai.service), never trusted.
"""

import enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import RecoveryAction


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AIRecommendationOutput(BaseModel):
    """Validated shape of the JSON Qwen must return. `recommended_action`
    and `alternative_action` are restricted to the same five bounded
    actions Phase 4 already knows about -- the model can never invent a
    new one; Pydantic rejects anything else."""

    recommended_action: RecoveryAction
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=500)
    risk_level: RiskLevel
    customer_context: str = Field(min_length=1, max_length=500)
    alternative_action: Optional[RecoveryAction] = None

    @field_validator("recommended_action", "alternative_action", mode="before")
    @classmethod
    def _normalize_action(cls, value):
        # A 3B local model is inconsistent about case ("RETRY_PAYMENT" vs
        # "retry_payment") -- normalize before validating against the enum
        # rather than rejecting an otherwise-valid answer over casing.
        if value is None or isinstance(value, RecoveryAction):
            return value
        return str(value).strip().lower()

    @field_validator("risk_level", mode="before")
    @classmethod
    def _normalize_risk(cls, value):
        if isinstance(value, RiskLevel):
            return value
        return str(value).strip().upper()
