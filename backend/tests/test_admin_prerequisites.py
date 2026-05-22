import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer test-admin-token-xyz"}


@pytest.mark.asyncio
async def test_create_module_with_prerequisites(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/admin/modules", json={
            "topic": "stocks", "title": "Prereq Module", "icon": "📈",
            "order_index": 0, "prerequisite_ids": [], "min_age": None, "max_age": None,
        }, headers=admin_headers)
        assert r1.status_code == 200
        prereq_id = r1.json()["id"]

        r2 = await ac.post("/admin/modules", json={
            "topic": "risk", "title": "Risk Module", "icon": "⚠️",
            "order_index": 1, "prerequisite_ids": [prereq_id], "min_age": 10, "max_age": 16,
        }, headers=admin_headers)
        assert r2.status_code == 200
        data = r2.json()
        assert data["prerequisite_ids"] == [prereq_id]
        assert data["min_age"] == 10
        assert data["max_age"] == 16


@pytest.mark.asyncio
async def test_create_module_self_reference_rejected(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/admin/modules", json={
            "topic": "stocks", "title": "Self Ref", "icon": "📈", "order_index": 0,
        }, headers=admin_headers)
        assert r1.status_code == 200
        mod_id = r1.json()["id"]

        r2 = await ac.put(f"/admin/modules/{mod_id}", json={
            "prerequisite_ids": [mod_id],
        }, headers=admin_headers)
        assert r2.status_code == 400
        assert "self-reference" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_module_nonexistent_prerequisite_rejected(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        fake_id = str(uuid.uuid4())
        r = await ac.post("/admin/modules", json={
            "topic": "stocks", "title": "Bad Prereq", "icon": "📈",
            "order_index": 0, "prerequisite_ids": [fake_id],
        }, headers=admin_headers)
        assert r.status_code == 400
        assert "not found" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_modules_includes_new_fields(admin_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/admin/modules", json={
            "topic": "savings", "title": "Age Test", "icon": "🏦",
            "order_index": 0, "min_age": 8, "max_age": 12,
        }, headers=admin_headers)

        r = await ac.get("/admin/modules", headers=admin_headers)
        assert r.status_code == 200
        modules = r.json()
        mod = next(m for m in modules if m["title"] == "Age Test")
        assert mod["min_age"] == 8
        assert mod["max_age"] == 12
        assert "prerequisite_ids" in mod
