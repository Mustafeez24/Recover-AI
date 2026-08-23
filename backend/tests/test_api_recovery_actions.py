from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models import Customer, FailureCategory, Payment, PaymentMethod, PaymentStatus, RecoveryCase, RecoveryCaseStatus, RecoveryPriority


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _seed_case(db_session, case_id="rec_api1", success=9, failed=1, amount=1000.0):
    customer = Customer(
        customer_id="cus_api_wf",
        customer_since=date(2024, 1, 1),
        total_successful_payments=success,
        total_failed_payments=failed,
        lifetime_value=8000.0,
        created_at=datetime.utcnow(),
    )
    db_session.add(customer)
    db_session.commit()

    payment = Payment(
        payment_id="pay_api_wf",
        customer_id=customer.customer_id,
        subscription_id=None,
        amount=amount,
        currency="INR",
        payment_status=PaymentStatus.FAILED,
        failure_reason=None,
        payment_method=PaymentMethod.CARD,
        created_at=datetime(2024, 1, 1),
        retry_count=0,
    )
    db_session.add(payment)
    db_session.commit()

    case = RecoveryCase(
        recovery_case_id=case_id,
        payment_id=payment.payment_id,
        customer_id=customer.customer_id,
        status=RecoveryCaseStatus.DETECTED.value,
        priority=RecoveryPriority.MEDIUM,
        amount_at_risk=amount,
        customer_value=8000.0,
        failure_category=FailureCategory.TEMPORARY_FAILURE,
        detection_reason="test",
        recommended_next_step="test",
        created_at=datetime.utcnow(),
    )
    db_session.add(case)
    db_session.commit()
    return case


def test_plan_endpoint(client, db_session):
    case = _seed_case(db_session)
    response = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    assert response.status_code == 200
    body = response.json()
    assert body["already_planned"] is False
    assert body["action"] == "retry_payment"
    assert body["status"] == "planned"


def test_plan_endpoint_is_idempotent(client, db_session):
    case = _seed_case(db_session)
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    second = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    assert second.json()["already_planned"] is True


def test_validate_endpoint(client, db_session):
    case = _seed_case(db_session)
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    response = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/validate")
    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["status"] == "validated"


def test_execute_endpoint_success(client, db_session):
    case = _seed_case(db_session, success=9, failed=1, amount=1000.0)  # strong history -> recovers
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/validate")
    response = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/execute")
    assert response.status_code == 200
    body = response.json()
    assert body["execution_status"] == "success"
    assert body["recovered_amount"] == 1000.0
    assert body["status"] == "recovered"


def test_execute_endpoint_before_validate_fails(client, db_session):
    case = _seed_case(db_session)
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    response = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/execute")
    assert response.status_code == 400


def test_execute_endpoint_is_idempotent(client, db_session):
    case = _seed_case(db_session, success=9, failed=1)
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/validate")
    first = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/execute")
    second = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/execute")
    assert first.json()["recovered_amount"] == second.json()["recovered_amount"]
    assert second.json()["already_executed"] is True


def test_history_endpoint(client, db_session):
    case = _seed_case(db_session, success=9, failed=1)
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/validate")
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/execute")

    response = client.get(f"/api/recovery/opportunities/{case.recovery_case_id}/history")
    assert response.status_code == 200
    body = response.json()
    assert body["current_status"] == "recovered"
    assert len(body["history"]) == 4


def test_action_summary_endpoint(client, db_session):
    case = _seed_case(db_session, success=9, failed=1, amount=750.0)
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/plan")
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/validate")
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/execute")

    response = client.get("/api/recovery/action-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["total_opportunities"] == 1
    assert body["recovered_cases"] == 1
    assert body["simulated_recovered_revenue"] == 750.0


def test_action_summary_endpoint_empty_dataset(client, db_session):
    response = client.get("/api/recovery/action-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["total_opportunities"] == 0
    assert body["simulated_recovered_revenue"] == 0.0


def test_plan_endpoint_missing_case_returns_404(client, db_session):
    response = client.post("/api/recovery/opportunities/rec_does_not_exist/plan")
    assert response.status_code == 404


def test_validate_endpoint_missing_case_returns_404(client, db_session):
    response = client.post("/api/recovery/opportunities/rec_does_not_exist/validate")
    assert response.status_code == 404


def test_execute_endpoint_missing_case_returns_404(client, db_session):
    response = client.post("/api/recovery/opportunities/rec_does_not_exist/execute")
    assert response.status_code == 404


def test_history_endpoint_missing_case_returns_404(client, db_session):
    response = client.get("/api/recovery/opportunities/rec_does_not_exist/history")
    assert response.status_code == 404
