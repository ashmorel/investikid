from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Publicly known source default — fine for dev/CI, REJECTED in production
# by Settings._guard_admin_token so it can never silently authenticate prod.
_DEFAULT_ADMIN_TOKEN = "test-admin-token-xyz"  # nosec B105


def _ensure_asyncpg(url: str) -> str:
    """Convert postgresql:// to postgresql+asyncpg:// for SQLAlchemy async."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    database_url: str
    test_database_url: str

    @model_validator(mode="after")
    def _fix_db_urls(self) -> "Settings":
        self.database_url = _ensure_asyncpg(self.database_url)
        self.test_database_url = _ensure_asyncpg(self.test_database_url)
        return self

    @model_validator(mode="after")
    def _guard_admin_token(self) -> "Settings":
        """Fail closed: never let the publicly known default authenticate prod."""
        if self.environment == "production" and self.admin_token in (
            "",
            _DEFAULT_ADMIN_TOKEN,
        ):
            raise ValueError(
                "ADMIN_TOKEN must be set to a strong, non-default value when "
                "ENVIRONMENT=production (the source default is publicly known)."
            )
        return self
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    resend_api_key: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""
    stripe_portal_config_id: str = ""
    email_backend: str = "logging"  # "logging" | "resend"
    email_from: str = "noreply@invest-ed.app"
    feedback_notify_email: str = ""
    app_base_url: str = "http://localhost:5173"
    data_retention_days: int = 30
    privacy_notice_version: str = "2026-05-16"
    admin_token: str = _DEFAULT_ADMIN_TOKEN

    # LLM / AI — lite + standard tiers (open-source models)
    llm_together_api_key: str = ""
    llm_together_base_url: str = "https://api.together.xyz/v1"
    llm_together_model: str = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"
    llm_groq_api_key: str = ""
    llm_groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_groq_model: str = "llama-3.1-8b-instant"
    llm_lite_providers: str = "together"
    llm_standard_providers: str = "together"
    # LLM / AI — premium tier (OpenAI or Anthropic)
    llm_premium_provider: str = "openai"  # "openai" | "anthropic"
    llm_premium_api_key: str = ""
    llm_premium_model: str = "gpt-4o"
    # Coach Eddie tutor
    tutor_max_messages_free: int = 6
    tutor_max_messages_premium: int = 12
    tutor_rate_limit_per_hour: int = 10
    tutor_max_input_chars: int = 200
    tutor_max_response_tokens: int = 150

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
