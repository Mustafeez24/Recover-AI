from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models import Customer, FailureReason, Payment, PaymentMethod, PaymentStatus


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _seed(db_session):
    customer = Customer(
        customer_id="cus_api",
        customer_since=date(2024, 1, 1),
        total_successful_payments=8,
        total_failed_payments=2,
        lifetime_value=5000.0,
        created_at=datetime.utcnow(),
    )
    db_session.add(customer)
    db_session.commit()

    high_value = Payment(
        payment_id="pay_api_high",
        customer_id="cus_api",
        subscription_id=None,
        amount=3000.0,
        currency="INR",
        payment_status=PaymentStatus.FAILED,
        failure_reason=FailureReason.TEMPORARY_FAILURE,
        payment_method=PaymentMethod.CARD,
        created_at=datetime(2024, 1, 1),
        retry_count=0,
    )
    low_value = Payment(
        payment_id="pay_api_low",
        customer_id="cus_api",
        subscription_id=None,
        amount=150.0,
        currency="INR",
        payment_status=PaymentStatus.ABANDONED,
        failure_reason=FailureReason.CHECKOUT_ABANDONED,
        payment_method=None,
        created_at=datetime(2024, 1, 2),
        retry_count=0,
    )
    db_session.add_all([high_value, low_value])
    db_session.commit()


def test_detect_endpoint_creates_opportunities(client, db_session):
    _seed(db_session)
    response = client.post("/api/recovery/detect")
    assert response.status_code == 200
    body = response.json()
    assert body["run"]["opportunities_created"] == 2
    assert body["summary"]["recovery_opportunities"] == 2


def test_detect_endpoint_is_idempotent(client, db_session):
    _seed(db_session)
    client.post("/api/recovery/detect")
    second = client.post("/api/recovery/detect")
    assert second.json()["run"]["opportunities_created"] == 0


def test_list_opportunities_endpoint(client, db_session):
    _seed(db_session)
    client.post("/api/recovery/detect")

    response = client.get("/api/recovery/opportunities")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["opportunities"]) == 2


def test_list_opportunities_filter_by_min_amount(client, db_session):
    _seed(db_session)
    client.post("/api/recovery/detect")

    response = client.get("/api/recovery/opportunities", params={"min_amount": 1000})
    body = response.json()
    assert body["total"] == 1
    assert body["opportunities"][0]["payment_id"] == "pay_api_high"


def test_list_opportunities_filter_by_priority(client, db_session):
    _seed(db_session)
    client.post("/api/recovery/detect")

    response = client.get("/api/recovery/opportunities", params={"priority": "high"})
    body = response.json()
    for opp in body["opportunities"]:
        assert opp["priority"] == "high"


def test_get_single_opportunity(client, db_session):
    _seed(db_session)
    client.post("/api/recovery/detect")

    response = client.get("/api/recovery/opportunities/rec_pay_api_high")
    assert response.status_code == 200
    body = response.json()
    assert body["payment_id"] == "pay_api_high"
    assert body["payment"]["amount"] == 3000.0
    assert body["customer"]["customer_id"] == "cus_api"


def test_get_single_opportunity_not_found(client, db_session):
    response = client.get("/api/recovery/opportunities/rec_does_not_exist")
    assert response.status_code == 404


def test_summary_endpoint(client, db_session):
    _seed(db_session)
    client.post("/api/recovery/detect")

    response = client.get("/api/recovery/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["recovery_opportunities"] == 2
    assert body["total_revenue_at_risk"] == 3150.0


def test_summary_endpoint_empty_dataset(client, db_session):
    response = client.get("/api/recovery/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["recovery_opportunities"] == 0
    assert body["total_revenue_at_risk"] == 0
