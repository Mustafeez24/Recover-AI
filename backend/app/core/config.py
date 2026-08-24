from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RecoverAI"
    environment: str = "development"

    database_url: str = "postgresql://recoverai:recoverai@localhost:5432/recoverai"

    cors_origins: list[str] = ["http://localhost:3000"]

    # Phase 5: local Ollama AI provider. No API key -- it's a local server.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
