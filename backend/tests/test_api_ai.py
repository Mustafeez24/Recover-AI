from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from app.ai.provider import AIProvider, AIProviderUnavailableError
from app.api.recovery import get_ai_provider
from app.db.session import get_db
from app.main import app
from app.models import Customer, FailureCategory, Payment, PaymentMethod, PaymentStatus, RecoveryCase, RecoveryCaseStatus, RecoveryPriority


class FakeAIProvider(AIProvider):
    def __init__(self, response_text=None, raise_error=None, available=True, model="fake-model"):
        self.response_text = response_text
        self.raise_error = raise_error
        self.available = available
        self.model = model

    def complete(self, system_prompt, user_prompt):
        if self.raise_error:
            raise self.raise_error
        return self.response_text

    def is_available(self):
        return self.available


VALID_JSON = """{
  "recommended_action": "RETRY_PAYMENT",
  "confidence": 0.82,
  "reason": "Temporary failure with a strong customer history.",
  "risk_level": "LOW",
  "customer_context": "Customer has a strong payment history.",
  "alternative_action": "SCHEDULE_RETRY"
}"""


@pytest.fixture()
def client_factory(db_session):
    def _make(provider: AIProvider):
        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_ai_provider] = lambda: provider
        return TestClient(app)

    yield _make
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_ai_provider, None)


def _seed_case(db_session, case_id="rec_api_ai1", success=9, failed=1, amount=1000.0):
    customer = Customer(
        customer_id=f"cus_{case_id}",
        customer_since=date(2024, 1, 1),
        total_successful_payments=success,
        total_failed_payments=failed,
        lifetime_value=8000.0,
        created_at=datetime.utcnow(),
    )
    db_session.add(customer)
    db_session.commit()

    payment = Payment(
        payment_id=f"pay_{case_id}",
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


def test_ai_recommend_endpoint_success(client_factory, db_session):
    case = _seed_case(db_session)
    client = client_factory(FakeAIProvider(response_text=VALID_JSON))

    response = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/ai-recommend")
    assert response.status_code == 200
    body = response.json()
    assert body["ai_status"] == "ok"
    assert body["ai_recommended_action"] == "retry_payment"
    assert body["deterministic_action"] == "retry_payment"
    assert body["agreement"] is True
    assert "ai_model" in body


def test_ai_recommend_endpoint_ai_unavailable_falls_back(client_factory, db_session):
    case = _seed_case(db_session)
    client = client_factory(FakeAIProvider(raise_error=AIProviderUnavailableError("down")))

    response = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/ai-recommend")
    assert response.status_code == 200
    body = response.json()
    assert body["ai_status"] == "unavailable"
    assert body["fallback_used"] is True
    assert body["effective_action"] == body["deterministic_action"]


def test_ai_recommend_endpoint_missing_case_404(client_factory, db_session):
    client = client_factory(FakeAIProvider(response_text=VALID_JSON))
    response = client.post("/api/recovery/opportunities/rec_missing/ai-recommend")
    assert response.status_code == 404


def test_ai_recommend_endpoint_does_not_leak_system_prompt(client_factory, db_session):
    case = _seed_case(db_session)
    client = client_factory(FakeAIProvider(response_text=VALID_JSON))
    response = client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/ai-recommend")
    body_text = response.text
    assert "revenue recovery recommendation assistant" not in body_text


def test_ai_batch_analyze_endpoint(client_factory, db_session):
    _seed_case(db_session, case_id="rec_batch1")
    _seed_case(db_session, case_id="rec_batch2")
    client = client_factory(FakeAIProvider(response_text=VALID_JSON))

    response = client.post("/api/recovery/ai/analyze", params={"batch_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["cases_processed"] == 2
    assert all(r["ai_status"] == "ok" for r in body["results"])


def test_ai_batch_analyze_respects_batch_size(client_factory, db_session):
    for i in range(5):
        _seed_case(db_session, case_id=f"rec_batchsize{i}")
    client = client_factory(FakeAIProvider(response_text=VALID_JSON))

    response = client.post("/api/recovery/ai/analyze", params={"batch_size": 2})
    assert response.status_code == 200
    assert response.json()["cases_processed"] == 2


def test_ai_batch_analyze_skips_already_analyzed_cases(client_factory, db_session):
    _seed_case(db_session, case_id="rec_batchdup")
    client = client_factory(FakeAIProvider(response_text=VALID_JSON))

    first = client.post("/api/recovery/ai/analyze", params={"batch_size": 10})
    assert first.json()["cases_processed"] == 1

    second = client.post("/api/recovery/ai/analyze", params={"batch_size": 10})
    assert second.json()["cases_processed"] == 0


def test_ai_batch_analyze_handles_per_case_failure_without_breaking_batch(client_factory, db_session):
    _seed_case(db_session, case_id="rec_batcherr1")
    _seed_case(db_session, case_id="rec_batcherr2")
    client = client_factory(FakeAIProvider(response_text="not valid json"))

    response = client.post("/api/recovery/ai/analyze", params={"batch_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["cases_processed"] == 2
    assert all(r["ai_status"] == "invalid_json" for r in body["results"])


def test_ai_summary_endpoint(client_factory, db_session):
    case = _seed_case(db_session)
    client = client_factory(FakeAIProvider(response_text=VALID_JSON, available=True))
    client.post(f"/api/recovery/opportunities/{case.recovery_case_id}/ai-recommend")

    response = client.get("/api/recovery/ai-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["cases_analyzed"] == 1
    assert body["successful_recommendations"] == 1
    assert body["ollama_available"] is True


def test_ai_summary_endpoint_empty(client_factory, db_session):
    client = client_factory(FakeAIProvider())
    response = client.get("/api/recovery/ai-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["cases_analyzed"] == 0
    assert body["average_confidence"] is None


def test_ai_summary_reflects_ollama_unavailable(client_factory, db_session):
    client = client_factory(FakeAIProvider(available=False))
    response = client.get("/api/recovery/ai-summary")
    assert response.json()["ollama_available"] is False
