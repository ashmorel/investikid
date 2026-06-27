import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/internal/purge-accounts/run"


async def test_503_when_secret_unset(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "")
    r = await client.post(_PATH, headers={"X-Cron-Secret": "whatever"})
    assert r.status_code == 503
    assert r.json()["detail"] == "not_configured"


async def test_401_when_secret_missing_or_wrong(client, monkeypatch):
    """No CSRF token is sent — a 401 (not 403) proves the path is CSRF-exempt."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    assert (await client.post(_PATH)).status_code == 401
    assert (await client.post(_PATH, headers={"X-Cron-Secret": "nope"})).status_code == 401


async def test_200_runs_when_secret_matches(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")

    called = {}

    async def fake_purge(session, today):
        called["today"] = today
        return 3

    monkeypatch.setattr(internal.retention, "purge_expired_accounts", fake_purge)
    r = await client.post(_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    assert r.json() == {"purged": 3}
    assert "today" in called
