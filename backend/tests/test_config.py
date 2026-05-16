from app.core.config import settings


def test_settings_loads():
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.jwt_secret != ""
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 30


def test_compliance_config_defaults():
    from app.core.config import settings
    assert settings.data_retention_days == 30
    assert settings.privacy_notice_version == "2026-05-16"
