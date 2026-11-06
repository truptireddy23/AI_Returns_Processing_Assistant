"""Runtime settings, read from environment variables (and `.env` in local runs)."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# app/.env, wherever the process is started from (inside Docker the file doesn't
# exist and the variables come from docker-compose instead).
APP_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=APP_ENV_FILE, extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    log_json: bool = True

    # Any Postgres URL, e.g. the pooled connection string Neon gives you. Empty
    # means the local docker-compose database (returnguard.db.LOCAL_DATABASE_URL).
    database_url: SecretStr = SecretStr("")
    # Direct (non-pooled) URL for migrations and session features such as
    # LISTEN/NOTIFY. Neon provides it as DATABASE_URL_UNPOOLED; when empty,
    # DATABASE_URL is used.
    database_url_unpooled: SecretStr = SecretStr("")

    # Worker. The API wakes the worker over HTTP when it queues a job; the sweep is
    # only a backstop for a missed wake-up. It is long on purpose: every query
    # wakes a scale-to-zero database (Neon suspends after 5 idle minutes).
    worker_sweep_seconds: float = 1800.0
    # 0.0.0.0 inside Docker (reachable only on the compose network); use 127.0.0.1
    # when running the worker directly on a laptop.
    worker_wake_host: str = "0.0.0.0"  # noqa: S104
    worker_wake_port: int = 8001
    worker_wake_url: str = ""  # e.g. http://worker:8001/wake; empty = no wake-ups
    job_max_attempts: int = 3
    job_retry_seconds: tuple[int, ...] = (30, 120)  # wait before attempt 2, 3, ...
    job_stale_seconds: int = 600  # a "running" job older than this was abandoned
    # Serverless hosts (Vercel) have no worker process: the API runs the jobs itself
    # after the response, retries included, for up to this long. Keep it under the
    # function's maximum duration (300 s on Vercel Hobby).
    run_jobs_inline: bool = False
    inline_job_budget_seconds: float = 240.0
    # Bearer token for the scheduled backstop sweep (Vercel Cron sends CRON_SECRET).
    # Empty disables the sweep route.
    cron_secret: SecretStr = SecretStr("")

    # When the API is publicly reachable (its own Vercel project), it only serves
    # requests that carry this secret, which the Next.js proxy adds. The proxy also
    # passes the browser's address, so rate limits stay per client. Empty = off.
    api_proxy_secret: SecretStr = SecretStr("")

    # Auth
    session_ttl_hours: int = 12
    cookie_secure: bool = False  # must be true in production (HTTPS only)
    login_rate_limit: str = "10/minute"  # per client IP
    login_account_failure_limit: str = "20/hour"  # failed attempts per account
    signup_rate_limit: str = "5/hour"  # new accounts per client IP

    # Public write endpoints (per client IP)
    checkout_rate_limit: str = "10/minute"
    return_rate_limit: str = "10/minute"
    chat_rate_limit: str = "20/minute"

    # Return photo storage. With AWS_ENDPOINT_URL_S3 set (Neon Object Storage,
    # pulled by `neon env pull`), photos go to the S3 bucket; otherwise to a
    # local folder (offline work and tests).
    storage_bucket: str = "return-photos"
    product_photo_bucket: str = "product-photos"
    aws_endpoint_url_s3: str = ""
    aws_access_key_id: SecretStr = SecretStr("")
    aws_secret_access_key: SecretStr = SecretStr("")
    aws_region: str = "us-east-2"
    local_storage_dir: str = str(Path(__file__).resolve().parents[3] / "storage")

    # Uploads
    upload_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    upload_max_pixels: int = 40_000_000  # ~ 8000 x 5000; guards against decompression bombs
    upload_max_side: int = 3000  # stored copies are scaled down to this

    # Seeding (local and test only)
    seed_dir: str = "../seed"

    # Model providers (M5). Chat and embeddings are configured separately because a
    # provider may offer one without the other (Groq has no embeddings API). Each
    # takes any OpenAI-compatible endpoint: a key, a base URL (empty = OpenAI) and a
    # model. The older OPENAI_API_KEY / OPENAI_CHAT_BASE_URL / POLICY_MODEL names
    # still work as fallbacks. The model-backed steps run when CHAT_API_KEY is set;
    # otherwise review_return() uses RuleSteps, which needs none of this.
    chat_api_key: SecretStr = Field(
        SecretStr(""), validation_alias=AliasChoices("chat_api_key", "openai_api_key")
    )
    chat_base_url: str = Field(
        "", validation_alias=AliasChoices("chat_base_url", "openai_chat_base_url")
    )
    chat_model: str = Field(
        "gpt-4o-mini", validation_alias=AliasChoices("chat_model", "policy_model")
    )
    chat_temperature: float = 0.0
    chat_stream_enabled: bool = True
    chat_tools_enabled: bool = True
    # Deployment-specific estimates, not a provider invoice. Unknown is NULL, never zero.
    chat_input_usd_per_million: Decimal | None = Field(None, ge=0)
    chat_output_usd_per_million: Decimal | None = Field(None, ge=0)
    # Provider-specific request fields, as JSON, sent as-is with every chat call,
    # e.g. CHAT_EXTRA_BODY={"reasoning_effort": "none"} for Qwen on Groq.
    chat_extra_body: dict[str, Any] = {}
    # Retries on 429/5xx, honoring the provider's Retry-After. Free tiers with a
    # low tokens-per-minute cap need more than the SDK's default of 2.
    chat_max_retries: int = 2
    # Embeddings are optional. Without EMBEDDING_API_KEY the policy step and chat
    # assist send the whole policy instead of retrieving the closest clauses.
    # policy_chunks.embedding is a fixed vector(1536) column
    # (models.EMBEDDING_DIMENSIONS), so the embedding model must return 1536
    # dimensions; EMBEDDING_DIMENSIONS asks models that support it (e.g. OpenAI's
    # text-embedding-3-*) to shorten their output. Changing models means
    # re-embedding the policy: clear policy_chunks.embedding, run `make embed-policy`.
    embedding_api_key: SecretStr = Field(
        SecretStr(""), validation_alias=AliasChoices("embedding_api_key", "openai_api_key")
    )
    embedding_base_url: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int | None = None
    policy_retrieval_k: int = 4

    @field_validator(
        "embedding_dimensions",
        "chat_input_usd_per_million",
        "chat_output_usd_per_million",
        mode="before",
    )
    @classmethod
    def _blank_means_unset(cls, value: object) -> object:
        # `EMBEDDING_DIMENSIONS=` in .env (as in .env.example) means "not set".
        return None if value == "" else value

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.environment == "production" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
