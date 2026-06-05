import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/internal/video-health/run"


async def test_503_when_secret_unset(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "")
    r = await client.post(_PATH, headers={"X-Cron-Secret": "whatever"})
    assert r.status_code == 503
    assert r.json()["detail"] == "not_configured"


async def test_401_when_secret_missing_or_wrong(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    assert (await client.post(_PATH)).status_code == 401
    r = await client.post(_PATH, headers={"X-Cron-Secret": "nope"})
    assert r.status_code == 401


async def test_200_runs_check_when_secret_matches(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")

    called = {}

    async def fake_run(session):
        called["yes"] = True
        return {"ok": 3, "dead": 0, "unknown": 1, "dead_items": []}

    monkeypatch.setattr(internal, "run", fake_run)
    r = await client.post(_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    body = r.json()
    assert called.get("yes") is True
    assert body["ok"] == 3 and body["dead"] == 0 and body["unknown"] == 1
    assert "dead_items" not in body  # summary only
