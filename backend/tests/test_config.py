from app.core.config import settings


def test_settings_loads():
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.jwt_secret != ""
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 30
