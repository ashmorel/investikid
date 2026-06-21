from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    stripe_price_id: str = ""  # legacy single price (monthly) — see plan_catalog
    stripe_price_id_monthly: str = ""
    stripe_price_id_annual: str = ""
    stripe_portal_config_id: str = ""
    email_backend: str = "logging"  # "logging" | "resend"
    email_from: str = "noreply@invest-ed.app"
    feedback_notify_email: str = ""
    admin_alert_email: str = ""
    admin_bootstrap_email: str = ""  # if set, that user is granted is_admin on each deploy (idempotent)
    cron_secret: str = ""  # shared secret for POST /internal/video-health/run (machine trigger)
    youtube_api_key: str = ""  # optional; enables embedding-disabled detection in video-health
    llm_alert_cooldown_seconds: int = 21600  # 6h — min gap between repeat alerts of the same kind
    app_base_url: str = "http://localhost:5173"
    data_retention_days: int = 30
    analytics_retention_days: int = 400  # raw product-analytics events (~13 months)
    archived_module_retention_days: int = 30  # archived modules hard-purged after this
    firebase_service_account_json: str = ""  # FCM service-account JSON contents; blank = push disabled
    privacy_notice_version: str = "2026-05-16"

    # LLM / AI — lite + standard tiers (open-source models)
    llm_together_api_key: str = ""
    llm_together_base_url: str = "https://api.together.xyz/v1"
    llm_together_model: str = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"
    llm_groq_api_key: str = ""
    llm_groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_groq_model: str = "llama-3.1-8b-instant"
    llm_gemini_api_key: str = ""
    llm_gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_gemini_flash_lite_model: str = "gemini-2.5-flash-lite"
    llm_gemini_flash_model: str = "gemini-2.5-flash"
    llm_lite_providers: str = "gemini_flash_lite,together"
    llm_standard_providers: str = "gemini_flash,together"
    # LLM / AI — premium tier (OpenAI or Anthropic)
    llm_premium_provider: str = "openai"  # "openai" | "anthropic"
    llm_premium_api_key: str = ""
    llm_premium_model: str = "gpt-5-mini"
    # LLM / AI — content-AUTHORING tier: a best-quality model for OFFLINE admin
    # content generation (curriculum designer + lesson/brief generation) only.
    # Child-facing AI stays on the premium tier. Falls back to premium when unset.
    llm_authoring_provider: str = "anthropic"  # "openai" | "anthropic"
    llm_authoring_api_key: str = ""
    llm_authoring_model: str = ""  # e.g. claude-opus-4-8 (set in env to enable)
    # Parent social login (public client identifiers — NOT secrets)
    google_web_client_id: str = ""
    google_ios_client_id: str = ""
    apple_services_id: str = ""
    apple_bundle_id: str = ""
    # Apple In-App Purchase (item 4A·A2) — leave blank to disable Apple IAP
    apple_iap_issuer_id: str = ""
    apple_iap_key_id: str = ""
    apple_iap_private_key: str = ""
    apple_iap_bundle_id: str = ""
    apple_iap_app_apple_id: int | None = None
    apple_iap_environment: str = "Sandbox"
    apple_iap_product_id: str = ""
    apple_iap_product_id_annual: str = ""
    google_play_package_name: str = ""
    google_play_service_account_json: str = ""  # service-account JSON key contents
    google_play_product_id: str = ""
    google_play_product_id_annual: str = ""

    # Cloudflare R2 — self-hosted curated video uploads (admin)
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_base_url: str = ""  # e.g. https://videos.investkid.app  (public R2/CDN domain, no trailing slash)
    r2_max_upload_bytes: int = 200 * 1024 * 1024  # 200 MB

    # Coach Penny tutor
    tutor_max_messages_free: int = 6
    tutor_max_messages_premium: int = 12
    tutor_rate_limit_per_hour: int = 10
    tutor_max_input_chars: int = 200
    # Output ceiling for Coach/tutor/chart-coach answers. Conciseness is enforced
    # by the prompts ("under 100 words", age-appropriate); this is only an anti-
    # truncation margin so a concise answer never gets cut off mid-sentence. 150
    # was below a ~100-word answer's token need, truncating responses.
    tutor_max_response_tokens: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
