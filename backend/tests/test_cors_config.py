"""Tests for CORS configuration and cookie SameSite behaviour."""
import pytest
from unittest.mock import patch

from app.core.config import Settings
from app.routers.auth import _cookie_samesite


def test_cors_origins_default_is_dev_localhost():
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        test_database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret="test-secret",
    )
    assert s.cors_origins == "http://localhost:5173"


def test_cors_origins_parsed_from_comma_separated():
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        test_database_url="sqlite+aiosqlite:///:memory:",
        jwt_secret="test-secret",
        cors_origins="http://localhost:5173,capacitor://localhost,https://invest-ed.app",
    )
    origins = [o.strip() for o in s.cors_origins.split(",") if o.strip()]
    assert origins == [
        "http://localhost:5173",
        "capacitor://localhost",
        "https://invest-ed.app",
    ]


def test_cookie_opts_lax_in_development():
    with patch("app.routers.auth.settings") as mock_settings:
        mock_settings.environment = "development"
        assert _cookie_samesite() == "lax"


def test_cookie_opts_none_in_production():
    with patch("app.routers.auth.settings") as mock_settings:
        mock_settings.environment = "production"
        assert _cookie_samesite() == "none"
