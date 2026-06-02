import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_module_with_lessons(admin_client):
    resp = await admin_client.post("/admin/modules", json={
        "topic": "engagement_test",
        "title": "Engagement Test Module",
        "icon": "📊",
        "is_premium": False,
        "country_codes": [],
        "order_index": 0,
    })
    assert resp.status_code == 200
    module_id = resp.json()["id"]

    await admin_client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "card",
        "content_json": {"title": "Engagement Card", "body": "Body text"},
        "xp_reward": 10,
        "order_index": 0,
    })
    return resp.json()


async def test_engagement_requires_admin(client):
    r = await client.get(f"/admin/modules/{uuid.uuid4()}/engagement")
    assert r.status_code in (401, 403)


async def test_engagement_404_for_unknown_module(admin_client):
    r = await admin_client.get(f"/admin/modules/{uuid.uuid4()}/engagement")
    assert r.status_code == 404


async def test_engagement_shape_for_seeded_module(admin_client):
    mod = await _seed_module_with_lessons(admin_client)
    r = await admin_client.get(f"/admin/modules/{mod['id']}/engagement")
    assert r.status_code == 200
    body = r.json()
    assert body["module_id"] == str(mod["id"])
    assert set(body) >= {"learners_started", "learners_completed", "completion_rate", "average_score", "lessons"}
    assert isinstance(body["lessons"], list)
    if body["lessons"]:
        le = body["lessons"][0]
        assert set(le) >= {"lesson_id", "type", "label", "order", "views", "completions", "completion_rate", "average_score", "drop_off"}
        assert le["order"] == 0
