"""Idempotent database seeding script for Phase 2 synthetic data.

Creates the required tables (if missing), generates the deterministic
synthetic dataset, and inserts only rows whose primary key isn't already
present. Because generation is deterministic (fixed seed), re-running this
script produces the exact same rows and therefore inserts nothing new the
second time -- safe to run repeatedly.

Usage:
    python -m app.data_generation.seed
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_generation.generator import generate_dataset
from app.db.session import Base, SessionLocal, engine
from app.models import Customer, Payment, Subscription


def create_tables():
    Base.metadata.create_all(bind=engine)


def _insert_new(session: Session, model, rows: list, pk_field: str) -> int:
    if not rows:
        return 0
    existing = {row[0] for row in session.execute(select(getattr(model, pk_field))).all()}
    new_rows = [r for r in rows if r[pk_field] not in existing]
    if new_rows:
        session.bulk_insert_mappings(model, new_rows)
    return len(new_rows)


def seed(session: Session = None, seed_value: int = 42) -> dict:
    own_session = session is None
    session = session or SessionLocal()
    try:
        customers, subscriptions, payments = generate_dataset(seed_value)

        inserted_customers = _insert_new(session, Customer, customers, "customer_id")
        session.commit()

        inserted_subscriptions = _insert_new(session, Subscription, subscriptions, "subscription_id")
        session.commit()

        inserted_payments = _insert_new(session, Payment, payments, "payment_id")
        session.commit()

        return {
            "customers_generated": len(customers),
            "customers_inserted": inserted_customers,
            "subscriptions_generated": len(subscriptions),
            "subscriptions_inserted": inserted_subscriptions,
            "payments_generated": len(payments),
            "payments_inserted": inserted_payments,
        }
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    create_tables()
    result = seed()
    print("Seeding complete:")
    for key, value in result.items():
        print(f"  {key}: {value}")
