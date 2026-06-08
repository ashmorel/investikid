import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

CARD = json.dumps({"title": "T", "body": "B"})


async def _make_level(admin_client) -> str:
    """Create a module + level via the admin API, returning the level id."""
    r = await admin_client.post("/admin/modules", json={
        "topic": "stocks", "title": "Gen Mod", "icon": "📈", "order_index": 0,
    })
    assert r.status_code == 200
    module_id = r.json()["id"]
    r = await admin_client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Level 1", "order_index": 0, "is_premium": False, "pass_threshold": 0.7,
    })
    assert r.status_code == 200
    return r.json()["id"]


async def test_generate_requires_admin(client):
    resp = await client.post(
        "/admin/levels/00000000-0000-0000-0000-000000000000/generate",
        json={"concept": "x", "count": 1, "types": ["card"]},
    )
    assert resp.status_code in (401, 403)


async def test_generate_happy_path(admin_client):
    level_id = await _make_level(admin_client)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=CARD)
    with patch("app.services.admin_content_generation_service.get_llm_client", return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        resp = await admin_client.post(
            f"/admin/levels/{level_id}/generate",
            json={"concept": "compound interest", "count": 2, "types": ["card"]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["created"]) == 2 and body["skipped"] == 0


async def test_generate_unknown_level_404(admin_client):
    resp = await admin_client.post(
        "/admin/levels/00000000-0000-0000-0000-000000000000/generate",
        json={"concept": "x", "count": 1, "types": ["card"]},
    )
    assert resp.status_code == 404
