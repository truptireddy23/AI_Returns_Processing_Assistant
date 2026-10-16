"""Runtime settings, read from environment variables (and `.env` in local runs)."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    log_json: bool = True

    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://returnguard:returnguard@localhost:5432/returnguard"
    )

    worker_poll_seconds: float = 2.0

    # Auth
    session_ttl_hours: int = 12
    cookie_secure: bool = False  # must be true in production (HTTPS only)
    login_rate_limit: str = "10/minute"  # per client IP
    login_account_failure_limit: str = "20/hour"  # failed attempts per account

    # Seeding (local and test only)
    seed_dir: str = "../seed"

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
