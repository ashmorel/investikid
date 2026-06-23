from app.core.config import Settings, settings


def _make(**kw):
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        test_database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret="test-secret",
        **kw,
    )


def test_app_base_url_gets_https_scheme_when_missing():
    # A scheme-less env value (APP_BASE_URL=app.investikid.ai) would otherwise
    # produce relative <a href> links that email clients can't make clickable.
    assert _make(app_base_url="app.investikid.ai").app_base_url == "https://app.investikid.ai"


def test_app_base_url_keeps_existing_scheme_and_strips_trailing_slash():
    assert _make(app_base_url="http://localhost:5173/").app_base_url == "http://localhost:5173"
    assert _make(app_base_url="https://app.investikid.ai").app_base_url == "https://app.investikid.ai"


def test_settings_loads():
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.jwt_secret != ""
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 30


def test_compliance_config_defaults():
    from app.core.config import settings
    assert settings.data_retention_days == 30
    assert settings.privacy_notice_version == "2026-05-16"
