"""TDD tests for the LLM provider health probe (probe_provider / probe_all_providers)
and the admin GET /admin/llm-status endpoint.

No real API calls are made — all clients and settings are mocked.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── probe_provider ────────────────────────────────────────────────────

async def test_probe_provider_ok_when_key_and_client_respond():
    """Provider with a key and a responsive client → ok: True."""
    from app.services.llm_client import probe_provider

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="OK")
    mock_builder = MagicMock(return_value=mock_client)
    mock_key_getter = MagicMock(return_value="valid-api-key")

    with patch(
        "app.services.llm_client._PROVIDER_BUILDERS",
        {"test_provider": (mock_builder, mock_key_getter)},
    ):
        result = await probe_provider("test_provider")

    assert result["provider"] == "test_provider"
    assert result["configured"] is True
    assert result["ok"] is True
    assert result["detail"] == "responded"


async def test_probe_provider_no_key_returns_configured_false():
    """Provider with an empty key → configured: False, ok: False."""
    from app.services.llm_client import probe_provider

    mock_builder = MagicMock()
    mock_key_getter = MagicMock(return_value="")

    with patch(
        "app.services.llm_client._PROVIDER_BUILDERS",
        {"gemini_flash_lite": (mock_builder, mock_key_getter)},
    ):
        result = await probe_provider("gemini_flash_lite")

    assert result["provider"] == "gemini_flash_lite"
    assert result["configured"] is False
    assert result["ok"] is False
    assert "no api key" in result["detail"]
    mock_builder.assert_not_called()


async def test_probe_provider_unknown_provider():
    """Provider name not in _PROVIDER_BUILDERS → configured: False, ok: False."""
    from app.services.llm_client import probe_provider

    with patch("app.services.llm_client._PROVIDER_BUILDERS", {}):
        result = await probe_provider("nonexistent_provider")

    assert result["provider"] == "nonexistent_provider"
    assert result["configured"] is False
    assert result["ok"] is False
    assert "unknown provider" in result["detail"]


async def test_probe_provider_client_raises_returns_ok_false():
    """Provider whose client.complete raises → ok: False with error summary."""
    from app.services.llm_client import probe_provider

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=RuntimeError("connection refused"))
    mock_builder = MagicMock(return_value=mock_client)
    mock_key_getter = MagicMock(return_value="some-key")

    with patch(
        "app.services.llm_client._PROVIDER_BUILDERS",
        {"together": (mock_builder, mock_key_getter)},
    ):
        result = await probe_provider("together")

    assert result["provider"] == "together"
    assert result["configured"] is True
    assert result["ok"] is False
    assert "RuntimeError" in result["detail"]
    assert "connection refused" in result["detail"]


async def test_probe_provider_detail_truncated_to_200_chars():
    """Very long exception messages are truncated to ≤200 chars."""
    from app.services.llm_client import probe_provider

    long_message = "x" * 500
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=ValueError(long_message))
    mock_builder = MagicMock(return_value=mock_client)
    mock_key_getter = MagicMock(return_value="key")

    with patch(
        "app.services.llm_client._PROVIDER_BUILDERS",
        {"together": (mock_builder, mock_key_getter)},
    ):
        result = await probe_provider("together")

    assert len(result["detail"]) <= 200


async def test_probe_provider_never_includes_key_in_output():
    """The API key must NEVER appear in any field of the returned dict."""
    from app.services.llm_client import probe_provider

    secret_key = "super-secret-api-key-123"
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=Exception(f"Auth failed: {secret_key}"))
    mock_builder = MagicMock(return_value=mock_client)
    mock_key_getter = MagicMock(return_value=secret_key)

    with patch(
        "app.services.llm_client._PROVIDER_BUILDERS",
        {"gemini_flash": (mock_builder, mock_key_getter)},
    ):
        result = await probe_provider("gemini_flash")

    # The key getter returns the secret — but it must NOT appear in the result
    output_str = str(result)
    assert secret_key not in output_str


# ── probe_all_providers ───────────────────────────────────────────────

async def test_probe_all_providers_returns_list_for_each_provider():
    """probe_all_providers returns one entry per provider including premium."""
    from app.services.llm_client import probe_all_providers

    async def _mock_probe(name: str) -> dict:
        return {"provider": name, "configured": True, "ok": True, "detail": "responded"}

    mock_premium = AsyncMock()
    mock_premium.complete = AsyncMock(return_value="OK")

    with patch("app.services.llm_client.probe_provider", side_effect=_mock_probe), \
         patch("app.services.llm_client.get_strict_premium_client", return_value=mock_premium), \
         patch("app.services.llm_client.get_model_name", return_value="gpt-5-mini"):
        results = await probe_all_providers()

    providers = [r["provider"] for r in results]
    assert "gemini_flash_lite" in providers
    assert "gemini_flash" in providers
    assert "together" in providers
    assert "premium" in providers
    assert len(results) == 4


async def test_probe_all_providers_premium_ok():
    """When premium client responds, premium entry has ok: True."""
    from app.services.llm_client import probe_all_providers

    async def _mock_probe(name: str) -> dict:
        return {"provider": name, "configured": True, "ok": True, "detail": "responded"}

    mock_premium = AsyncMock()
    mock_premium.complete = AsyncMock(return_value="OK")

    with patch("app.services.llm_client.probe_provider", side_effect=_mock_probe), \
         patch("app.services.llm_client.get_strict_premium_client", return_value=mock_premium), \
         patch("app.services.llm_client.get_model_name", return_value="gpt-5-mini"):
        results = await probe_all_providers()

    premium = next(r for r in results if r["provider"] == "premium")
    assert premium["ok"] is True
    assert premium["configured"] is True
    assert premium["model"] == "gpt-5-mini"


async def test_probe_all_providers_premium_not_configured():
    """When no premium key, premium entry has configured: False."""
    from app.services.llm_client import probe_all_providers

    async def _mock_probe(name: str) -> dict:
        return {"provider": name, "configured": False, "ok": False, "detail": "no api key set"}

    with patch("app.services.llm_client.probe_provider", side_effect=_mock_probe), \
         patch("app.services.llm_client.get_strict_premium_client", return_value=None):
        results = await probe_all_providers()

    premium = next(r for r in results if r["provider"] == "premium")
    assert premium["configured"] is False
    assert premium["ok"] is False
    assert "no premium key" in premium["detail"]


async def test_probe_all_providers_premium_client_fails():
    """When premium client raises, premium entry has ok: False with error detail."""
    from app.services.llm_client import probe_all_providers

    async def _mock_probe(name: str) -> dict:
        return {"provider": name, "configured": True, "ok": True, "detail": "responded"}

    mock_premium = AsyncMock()
    mock_premium.complete = AsyncMock(side_effect=ConnectionError("network error"))

    with patch("app.services.llm_client.probe_provider", side_effect=_mock_probe), \
         patch("app.services.llm_client.get_strict_premium_client", return_value=mock_premium), \
         patch("app.services.llm_client.get_model_name", return_value="gpt-5-mini"):
        results = await probe_all_providers()

    premium = next(r for r in results if r["provider"] == "premium")
    assert premium["ok"] is False
    assert "ConnectionError" in premium["detail"]


# ── GET /admin/llm-status endpoint ───────────────────────────────────

async def test_llm_status_requires_admin(client):
    """A non-admin authenticated user gets 403."""
    await client.post("/auth/register", json={
        "email": "nonadmin_llm@example.com",
        "username": "nonadmin_llm",
        "password": "SecurePass123!",
        "dob": "2010-05-10",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent_llm@example.com",
    })
    await client.post("/auth/login", json={
        "email": "nonadmin_llm@example.com",
        "password": "SecurePass123!",
    })
    resp = await client.get("/admin/llm-status")
    assert resp.status_code == 403


async def test_llm_status_unauthenticated_returns_401(client):
    """Unauthenticated request to /admin/llm-status returns 401."""
    # Use a fresh client-like approach: make a request without logging in
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/llm-status")
    assert resp.status_code in (401, 403)


async def test_llm_status_admin_returns_200_list(admin_client):
    """Admin user gets 200 with a list of provider probe results."""
    fake_results = [
        {"provider": "gemini_flash_lite", "configured": True, "ok": True, "detail": "responded"},
        {"provider": "gemini_flash", "configured": True, "ok": True, "detail": "responded"},
        {"provider": "together", "configured": True, "ok": True, "detail": "responded"},
        {"provider": "premium", "model": "gpt-5-mini", "configured": True, "ok": True, "detail": "responded"},
    ]
    with patch("app.routers.admin_settings.probe_all_providers", AsyncMock(return_value=fake_results)):
        resp = await admin_client.get("/admin/llm-status")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 4
    providers = [item["provider"] for item in data]
    assert "gemini_flash_lite" in providers
    assert "premium" in providers


async def test_llm_status_response_contains_no_api_keys(admin_client):
    """The response must not include any API key material."""
    fake_results = [
        {"provider": "gemini_flash_lite", "configured": True, "ok": False,
         "detail": "AuthError: bad credentials"},
    ]
    with patch("app.routers.admin_settings.probe_all_providers", AsyncMock(return_value=fake_results)):
        resp = await admin_client.get("/admin/llm-status")

    assert resp.status_code == 200
    # Verify no key-like strings appear (keys always start with known prefixes)
    body = resp.text
    for suspicious in ("sk-", "AIza", "gsk_", "tog-"):
        assert suspicious not in body
