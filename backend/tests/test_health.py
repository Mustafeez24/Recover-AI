import pytest
from fastapi.testclient import TestClient

from app.ai.provider import AIProvider
from app.api.health import get_ai_provider
from app.db.session import get_db
from app.main import app


class _FakeProvider(AIProvider):
    def __init__(self, available: bool, raises: bool = False):
        self._available = available
        self._raises = raises

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        if self._raises:
            raise RuntimeError("provider check blew up")
        return self._available


class _BrokenSession:
    """Stands in for a DB session whose connection is down."""

    def execute(self, *args, **kwargs):
        raise RuntimeError("connection refused")


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _override_provider(provider: AIProvider):
    app.dependency_overrides[get_ai_provider] = lambda: provider


def test_root():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_ok_database_and_ai_available(client):
    _override_provider(_FakeProvider(available=True))
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok", "ai_provider": "available"}
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_health_ok_when_ai_provider_unavailable(client):
    """AI being unreachable is expected in production (Ollama is local/demo
    only) and must never affect overall status."""
    _override_provider(_FakeProvider(available=False))
    try:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database"] == "ok"
        assert body["ai_provider"] == "unavailable"
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_health_ok_when_ai_provider_check_raises(client):
    """is_available() is documented to never raise, but the health check
    must not trust that -- an exception here still must not 500."""
    _override_provider(_FakeProvider(available=True, raises=True))
    try:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["ai_provider"] == "unavailable"
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)


def test_health_degraded_when_database_unavailable():
    def override_get_db():
        yield _BrokenSession()

    app.dependency_overrides[get_db] = override_get_db
    _override_provider(_FakeProvider(available=True))
    try:
        response = TestClient(app).get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["database"] == "unavailable"
        assert body["ai_provider"] == "available"
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_ai_provider, None)
