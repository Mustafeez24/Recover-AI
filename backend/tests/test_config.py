from app.core.config import Settings


def test_database_url_postgres_scheme_is_normalized():
    settings = Settings(database_url="postgres://user:pass@host:5432/db")
    assert settings.database_url == "postgresql://user:pass@host:5432/db"


def test_database_url_postgresql_scheme_is_left_unchanged():
    settings = Settings(database_url="postgresql://user:pass@host:5432/db")
    assert settings.database_url == "postgresql://user:pass@host:5432/db"


def test_cors_origins_env_override(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://recoverai.example.vercel.app"]')
    settings = Settings()
    assert settings.cors_origins == ["https://recoverai.example.vercel.app"]
