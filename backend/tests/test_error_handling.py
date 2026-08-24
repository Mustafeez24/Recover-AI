from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


def test_unhandled_exception_returns_structured_json_not_a_traceback():
    def broken_get_db():
        raise RuntimeError("simulated unexpected failure")

    app.dependency_overrides[get_db] = broken_get_db
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.get("/api/data/summary")
        assert response.status_code == 500
        body = response.json()
        assert body == {
            "error": "internal_server_error",
            "detail": "An unexpected error occurred.",
        }
        assert "RuntimeError" not in response.text
        assert "Traceback" not in response.text
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_http_exception_handling_is_unaffected_by_global_handler(db_session):
    """A regular 404 (e.g. an unknown recovery case) must still come back
    as FastAPI's normal HTTPException response, not the generic 500
    handler -- the global handler only catches truly unhandled errors."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = TestClient(app).get("/api/recovery/opportunities/does-not-exist")
        assert response.status_code == 404
        assert response.json() != {
            "error": "internal_server_error",
            "detail": "An unexpected error occurred.",
        }
    finally:
        app.dependency_overrides.pop(get_db, None)
