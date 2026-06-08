import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/internal/trial-reminders/run"


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


async def test_200_runs_when_secret_matches(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")

    called = {}

    async def fake_run(session):
        called["yes"] = True
        return {"sent": 2, "skipped": 1}

    monkeypatch.setattr(internal.trial_reminder_service, "run", fake_run)
    r = await client.post(_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    body = r.json()
    assert called.get("yes") is True
    assert "sent" in body and "skipped" in body
    assert body["sent"] == 2 and body["skipped"] == 1
