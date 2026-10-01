from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    """Runtime configuration loaded from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = INSECURE_DEFAULT_SECRET
    database_url: str = "postgresql+psycopg://football_ai:football_ai@localhost:5432/football_ai"
    default_timezone: str = "UTC"
    barcelona_external_team_id: str | None = None
    web_url: str = "http://localhost:3000"
    football_provider: str = "sportmonks"
    sportmonks_api_token: str | None = None
    sportmonks_base_url: str = "https://api.sportmonks.com/v3/football"
    provider_timeout_seconds: float = 15.0
    scheduler_sync_interval_seconds: int = 21600
    scheduler_dispatch_interval_seconds: int = 60
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    llm_model: str | None = None
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-in-production"
    session_cookie_name: str = "football_ai_session"
    max_request_bytes: int = Field(default=1_000_000, ge=1024, le=10_000_000)
    job_retry_base_seconds: int = Field(default=60, ge=1, le=3600)

    def validate_runtime_security(self) -> None:
        """Fail fast only in deployed environments when placeholder credentials remain."""

        if self.app_env.lower() not in {"production", "staging"}:
            return
        invalid: list[str] = []
        if not self.app_secret_key or self.app_secret_key == INSECURE_DEFAULT_SECRET:
            invalid.append("APP_SECRET_KEY")
        if len(self.app_secret_key) < 32:
            invalid.append("APP_SECRET_KEY (at least 32 characters)")
        if not self.admin_password or self.admin_password == INSECURE_DEFAULT_SECRET:
            invalid.append("ADMIN_PASSWORD")
        if invalid:
            raise RuntimeError(
                "Unsafe production configuration: set " + ", ".join(dict.fromkeys(invalid))
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
