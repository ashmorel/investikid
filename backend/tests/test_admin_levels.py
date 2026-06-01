import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_module(admin_client):
    r = await admin_client.post("/admin/modules", json={
        "topic": "stocks", "title": "Admin LV Mod", "icon": "📈", "order_index": 0,
    })
    assert r.status_code == 200
    return r.json()["id"]


async def test_level_crud_and_lessons(admin_client):
    module_id = await _make_module(admin_client)

    r = await admin_client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Level 1", "order_index": 0, "is_premium": False, "pass_threshold": 0.7,
    })
    assert r.status_code == 200
    level_id = r.json()["id"]
    assert r.json()["content_source"] == "authored"

    r = await admin_client.get(f"/admin/modules/{module_id}/levels")
    assert r.status_code == 200 and len(r.json()) == 1

    r = await admin_client.post(f"/admin/levels/{level_id}/lessons", json={
        "type": "video", "order_index": 0, "xp_reward": 10,
        "content_json": {"youtube_id": "abc123", "caption": "Intro"},
    })
    assert r.status_code == 200
    assert r.json()["type"] == "video"

    r = await admin_client.put(f"/admin/levels/{level_id}", json={"is_premium": True})
    assert r.status_code == 200 and r.json()["is_premium"] is True

    r = await admin_client.delete(f"/admin/levels/{level_id}")
    assert r.status_code == 200


async def test_video_lesson_requires_youtube_id(admin_client):
    module_id = await _make_module(admin_client)
    r = await admin_client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "L1", "order_index": 0,
    })
    level_id = r.json()["id"]
    r = await admin_client.post(f"/admin/levels/{level_id}/lessons", json={
        "type": "video", "order_index": 0, "xp_reward": 10, "content_json": {"caption": "no id"},
    })
    assert r.status_code == 422
