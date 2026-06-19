import pytest

from app.services.app_settings import (
    get_enabled_content_languages,
    set_enabled_content_languages,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_defaults_empty_then_settable(db_session):
    assert await get_enabled_content_languages(db_session) == []
    await set_enabled_content_languages(db_session, ["fr", "es"])
    assert set(await get_enabled_content_languages(db_session)) == {"fr", "es"}


async def test_rejects_unsupported(db_session):
    with pytest.raises(ValueError):
        await set_enabled_content_languages(db_session, ["xx"])


async def test_admin_settings_roundtrip(admin_client):
    r = await admin_client.get("/admin/settings")
    assert r.status_code == 200
    assert r.json()["enabled_content_languages"] == []

    r = await admin_client.put(
        "/admin/settings",
        json={"alert_emails": ["ops@example.com"], "enabled_content_languages": ["fr"]},
    )
    assert r.status_code == 200
    assert r.json()["enabled_content_languages"] == ["fr"]
