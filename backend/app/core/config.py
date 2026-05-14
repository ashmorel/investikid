from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    test_database_url: str
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    environment: str = "development"
    resend_api_key: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    email_backend: str = "logging"  # "logging" | "resend"
    email_from: str = "noreply@invest-ed.app"
    app_base_url: str = "http://localhost:5173"

    # LLM / AI — free tier (Gemini Flash via Google's OpenAI-compatible API)
    llm_free_api_key: str = ""
    llm_free_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_free_model: str = "gemini-2.5-flash-lite"
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
