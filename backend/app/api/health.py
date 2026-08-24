from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider
from app.ai.service import get_default_provider
from app.db.session import get_db

router = APIRouter(tags=["health"])


def get_ai_provider() -> AIProvider:
    return get_default_provider()


@router.get("/health")
def health_check(
    db: Session = Depends(get_db),
    provider: AIProvider = Depends(get_ai_provider),
):
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        # A health check must never raise -- a broken DB is reported as a
        # degraded status, not a 500.
        database_status = "unavailable"

    try:
        ai_provider_status = "available" if provider.is_available() else "unavailable"
    except Exception:
        ai_provider_status = "unavailable"

    return {
        # The AI provider is optional and advisory (Phase 5); it being
        # unavailable is an expected production state (see README §9), so
        # it never affects overall status. The database is required.
        "status": "ok" if database_status == "ok" else "degraded",
        "database": database_status,
        "ai_provider": ai_provider_status,
    }
