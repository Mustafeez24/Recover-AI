"""Safe, additive Phase 5 schema migration.

Creates the new `ai_recommendations` table only. No existing table
(customers, subscriptions, payments, recovery_cases,
recovery_action_history) is dropped, altered, or rewritten -- all
Phase 1-4 data is untouched.

Usage:
    python -m app.db.migrate_phase5
"""

from app.db.session import Base, engine


def run_migration():
    import app.models  # noqa: F401  (registers all models on Base.metadata)

    Base.metadata.create_all(bind=engine)
    return {"status": "ai_recommendations table ensured"}


if __name__ == "__main__":
    result = run_migration()
    print("Phase 5 migration complete:")
    for key, value in result.items():
        print(f"  {key}: {value}")
