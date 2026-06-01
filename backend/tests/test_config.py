import pytest
from pydantic import ValidationError

from app.core.config import _DEFAULT_ADMIN_TOKEN, Settings, settings

_REQUIRED = {
    "database_url": "postgresql://u:p@localhost/db",
    "test_database_url": "postgresql://u:p@localhost/test",
    "jwt_secret": "x" * 32,
}


def test_settings_loads():
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.jwt_secret != ""
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 30


def test_compliance_config_defaults():
    from app.core.config import settings
    assert settings.data_retention_days == 30
    assert settings.privacy_notice_version == "2026-05-16"


def test_production_rejects_default_admin_token():
    with pytest.raises(ValidationError):
        Settings(**_REQUIRED, environment="production",
                 admin_token=_DEFAULT_ADMIN_TOKEN, _env_file=None)


def test_production_rejects_empty_admin_token():
    with pytest.raises(ValidationError):
        Settings(**_REQUIRED, environment="production",
                 admin_token="", _env_file=None)


def test_production_accepts_strong_admin_token():
    s = Settings(**_REQUIRED, environment="production",
                 admin_token="a-strong-unique-secret-value", _env_file=None)
    assert s.admin_token == "a-strong-unique-secret-value"


def test_non_production_allows_default_admin_token():
    s = Settings(**_REQUIRED, environment="development",
                 admin_token=_DEFAULT_ADMIN_TOKEN, _env_file=None)
    assert s.admin_token == _DEFAULT_ADMIN_TOKEN
