"""Safe, additive Phase 4 schema migration.

Adds the new columns Phase 4 needs to the existing `recovery_cases` table
and creates the new `recovery_action_history` audit table. Never drops or
rewrites existing tables/columns, so Phase 1-3 data (customers,
subscriptions, payments, and the recovery cases already detected) is
never touched. Every ALTER TABLE uses IF NOT EXISTS, and the one UPDATE
only touches rows still carrying the old Phase 2/3 default status value
-- so this script is safe to run more than once.

There is no migration framework (Alembic) in this project by design
(kept intentionally simple); this script is the "migration" for this
one schema change.

Usage:
    python -m app.db.migrate_phase4
"""

from sqlalchemy import text

from app.db.session import Base, engine
from app.models.enums import RecoveryCaseStatus

ALTER_STATEMENTS = [
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS action VARCHAR",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS action_reason VARCHAR",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS planned_at TIMESTAMP",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS last_validation_result VARCHAR",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS last_validation_reason VARCHAR",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS execution_status VARCHAR",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS executed_at TIMESTAMP",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS execution_failure_reason VARCHAR",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS recovered_amount NUMERIC(10, 2) NOT NULL DEFAULT 0",
    "ALTER TABLE recovery_cases ADD COLUMN IF NOT EXISTS recovery_attempts INTEGER NOT NULL DEFAULT 0",
]


def run_migration():
    with engine.begin() as conn:
        for statement in ALTER_STATEMENTS:
            conn.execute(text(statement))

        # Cases created by Phase 3 (before this migration) started life
        # with status="open"; the Phase 4 state machine starts at DETECTED.
        result = conn.execute(
            text("UPDATE recovery_cases SET status = :new_status WHERE status = 'open'"),
            {"new_status": RecoveryCaseStatus.DETECTED.value},
        )
        updated = result.rowcount

    # Creates recovery_action_history (new table) only; every other table
    # already exists and create_all() leaves it untouched.
    import app.models  # noqa: F401  (registers all models on Base.metadata)

    Base.metadata.create_all(bind=engine)

    return {"status_rows_migrated": updated}


if __name__ == "__main__":
    result = run_migration()
    print("Phase 4 migration complete:")
    for key, value in result.items():
        print(f"  {key}: {value}")
