import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")
H = {"Authorization": "Bearer test-admin-token-xyz"}


async def _make_module(client):
    r = await client.post("/admin/modules", json={
        "topic": "stocks", "title": "Admin LV Mod", "icon": "📈", "order_index": 0,
    }, headers=H)
    assert r.status_code == 200
    return r.json()["id"]


async def test_level_crud_and_lessons(client):
    module_id = await _make_module(client)

    r = await client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "Level 1", "order_index": 0, "is_premium": False, "pass_threshold": 0.7,
    }, headers=H)
    assert r.status_code == 200
    level_id = r.json()["id"]
    assert r.json()["content_source"] == "authored"

    r = await client.get(f"/admin/modules/{module_id}/levels", headers=H)
    assert r.status_code == 200 and len(r.json()) == 1

    r = await client.post(f"/admin/levels/{level_id}/lessons", json={
        "type": "video", "order_index": 0, "xp_reward": 10,
        "content_json": {"youtube_id": "abc123", "caption": "Intro"},
    }, headers=H)
    assert r.status_code == 200
    assert r.json()["type"] == "video"

    r = await client.put(f"/admin/levels/{level_id}", json={"is_premium": True}, headers=H)
    assert r.status_code == 200 and r.json()["is_premium"] is True

    r = await client.delete(f"/admin/levels/{level_id}", headers=H)
    assert r.status_code == 200


async def test_video_lesson_requires_youtube_id(client):
    module_id = await _make_module(client)
    r = await client.post(f"/admin/modules/{module_id}/levels", json={
        "title": "L1", "order_index": 0,
    }, headers=H)
    level_id = r.json()["id"]
    r = await client.post(f"/admin/levels/{level_id}/lessons", json={
        "type": "video", "order_index": 0, "xp_reward": 10, "content_json": {"caption": "no id"},
    }, headers=H)
    assert r.status_code == 422
