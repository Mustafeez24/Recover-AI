from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RecoverAI"
    environment: str = "development"

    database_url: str = "postgresql://recoverai:recoverai@localhost:5432/recoverai"

    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
