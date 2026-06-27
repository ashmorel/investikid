import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")
_PATH = "/internal/market-warm/run"


async def test_503_when_secret_unset(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "")
    assert (await client.post(_PATH, headers={"X-Cron-Secret": "x"})).status_code == 503


async def test_401_when_secret_wrong(client, monkeypatch):
    """No CSRF token sent — 401 (not 403) proves the path is CSRF-exempt."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    assert (await client.post(_PATH)).status_code == 401
    assert (await client.post(_PATH, headers={"X-Cron-Secret": "nope"})).status_code == 401


async def test_200_runs_when_secret_matches(client, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    monkeypatch.setattr(internal.market_warm_service, "warm_all",
                        lambda provider: {"regions": [{"region": "US", "featured": 3, "movers": True}]})
    r = await client.post(_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    assert r.json()["regions"][0]["region"] == "US"
