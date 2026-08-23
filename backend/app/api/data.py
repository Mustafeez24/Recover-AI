from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Customer, Payment, RecoveryCase, Subscription

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/summary")
def data_summary(db: Session = Depends(get_db)):
    customers_count = db.execute(select(func.count()).select_from(Customer)).scalar()
    subscriptions_count = db.execute(select(func.count()).select_from(Subscription)).scalar()
    payments_count = db.execute(select(func.count()).select_from(Payment)).scalar()
    recovery_cases_count = db.execute(select(func.count()).select_from(RecoveryCase)).scalar()

    status_rows = db.execute(
        select(Payment.payment_status, func.count()).group_by(Payment.payment_status)
    ).all()
    payments_by_status = {status.value: count for status, count in status_rows}

    return {
        "customers": customers_count,
        "subscriptions": subscriptions_count,
        "payments": payments_count,
        "payments_by_status": payments_by_status,
        "recovery_cases": recovery_cases_count,
    }
