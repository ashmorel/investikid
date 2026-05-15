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

    # LLM / AI — lite + standard tiers (open-source models)
    llm_together_api_key: str = ""
    llm_together_base_url: str = "https://api.together.xyz/v1"
    llm_together_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    llm_groq_api_key: str = ""
    llm_groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_groq_model: str = "llama-3.1-8b-instant"
    llm_lite_providers: str = "together,groq"
    llm_standard_providers: str = "together,groq"
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
