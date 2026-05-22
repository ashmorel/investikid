import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer test-admin-token-xyz"}


async def test_admin_stats_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/stats")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Missing or invalid admin token"


async def test_admin_stats_rejects_bad_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/stats", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401


async def test_admin_stats_accepts_valid_token(client, admin_headers):
    resp = await client.get("/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "modules" in data
    assert "lessons" in data
    assert "badges" in data
    assert "challenges" in data
