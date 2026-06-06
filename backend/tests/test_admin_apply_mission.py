import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_create_lesson_with_apply_mission(admin_client):
    mod = await admin_client.post("/admin/modules",
        json={"topic": "stocks", "title": "M", "order_index": 1})
    assert mod.status_code in (200, 201)
    module_id = mod.json()["id"]
    resp = await admin_client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "card", "content_json": {"title": "t", "body": "b"}, "xp_reward": 10, "order_index": 1,
        "apply_mission": {"mission_type": "first_buy", "params_json": {}, "title": "Buy one",
                          "prompt": "Try it!", "xp_reward": 20, "cash_reward": "100.00"},
    })
    assert resp.status_code in (200, 201)
    assert resp.json()["apply_mission"]["mission_type"] == "first_buy"


async def test_module_completion_cash_reward_roundtrip(admin_client):
    mod = await admin_client.post("/admin/modules",
        json={"topic": "stocks", "title": "M2", "order_index": 2, "completion_cash_reward": "250.00"})
    assert mod.status_code in (200, 201)
    module_id = mod.json()["id"]
    assert mod.json()["completion_cash_reward"] == "250.00"
    upd = await admin_client.put(f"/admin/modules/{module_id}",
        json={"completion_cash_reward": "300.00"})
    assert upd.status_code == 200
    assert upd.json()["completion_cash_reward"] == "300.00"


async def test_update_lesson_overwrites_apply_mission(admin_client):
    mod = await admin_client.post(
        "/admin/modules", json={"topic": "stocks", "title": "M4", "order_index": 4}
    )
    module_id = mod.json()["id"]
    created = await admin_client.post(
        f"/admin/modules/{module_id}/lessons",
        json={
            "type": "card", "content_json": {"title": "t", "body": "b"},
            "xp_reward": 10, "order_index": 1,
            "apply_mission": {"mission_type": "first_buy", "params_json": {}, "title": "Buy one",
                              "prompt": "Try it!", "xp_reward": 20},
        },
    )
    lesson_id = created.json()["id"]
    upd = await admin_client.put(
        f"/admin/lessons/{lesson_id}",
        json={"apply_mission": {"mission_type": "diversify", "params_json": {"n": 3},
                                "title": "Spread out", "prompt": "Hold three", "xp_reward": 30}},
    )
    assert upd.status_code == 200
    mission = upd.json()["apply_mission"]
    assert mission["mission_type"] == "diversify"
    assert mission["params_json"] == {"n": 3}
    assert mission["xp_reward"] == 30


async def test_invalid_mission_type_rejected(admin_client):
    mod = await admin_client.post("/admin/modules",
        json={"topic": "stocks", "title": "M3", "order_index": 3})
    module_id = mod.json()["id"]
    resp = await admin_client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "card", "content_json": {"title": "t", "body": "b"}, "xp_reward": 10, "order_index": 1,
        "apply_mission": {"mission_type": "NOT_A_TYPE", "params_json": {}, "title": "x",
                          "prompt": "y", "xp_reward": 20},
    })
    assert resp.status_code == 422
