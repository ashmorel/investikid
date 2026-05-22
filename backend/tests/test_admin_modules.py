import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

HEADERS = {"Authorization": "Bearer test-admin-token-xyz"}


async def test_module_crud_lifecycle(client):
    """Create → read → update → reorder → delete a module."""
    # Create
    resp = await client.post("/admin/modules", json={
        "topic": "test_topic", "title": "Test Module", "icon": "🧪",
        "is_premium": False, "country_codes": [], "order_index": 0,
    }, headers=HEADERS)
    assert resp.status_code == 200
    module = resp.json()
    module_id = module["id"]
    assert module["topic"] == "test_topic"
    assert module["lesson_count"] == 0

    # List
    resp = await client.get("/admin/modules", headers=HEADERS)
    assert resp.status_code == 200
    modules = resp.json()
    assert any(m["id"] == module_id for m in modules)

    # Update
    resp = await client.put(f"/admin/modules/{module_id}", json={
        "title": "Updated Module",
    }, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Module"

    # Delete
    resp = await client.delete(f"/admin/modules/{module_id}", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # Verify deleted
    resp = await client.get("/admin/modules", headers=HEADERS)
    assert not any(m["id"] == module_id for m in resp.json())


async def test_lesson_crud_lifecycle(client):
    """Create module → add lessons → reorder → update → delete."""
    # Create module first
    resp = await client.post("/admin/modules", json={
        "topic": "lessons_test", "title": "Lesson Test Module", "icon": "📝",
        "is_premium": False, "country_codes": [], "order_index": 0,
    }, headers=HEADERS)
    module_id = resp.json()["id"]

    # Create card lesson
    resp = await client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "card",
        "content_json": {"title": "Card Title", "body": "Card body"},
        "xp_reward": 10, "order_index": 0,
    }, headers=HEADERS)
    assert resp.status_code == 200
    lesson_id = resp.json()["id"]
    assert resp.json()["type"] == "card"

    # Create quiz lesson
    resp = await client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "quiz",
        "content_json": {
            "question": "Q?", "choices": ["A", "B"],
            "answer_index": 0, "explanation": "Because A",
        },
        "xp_reward": 25, "order_index": 1,
    }, headers=HEADERS)
    assert resp.status_code == 200

    # List lessons
    resp = await client.get(f"/admin/modules/{module_id}/lessons", headers=HEADERS)
    assert len(resp.json()) == 2

    # Update lesson
    resp = await client.put(f"/admin/lessons/{lesson_id}", json={
        "content_json": {"title": "Updated Card", "body": "Updated body"},
    }, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["content_json"]["title"] == "Updated Card"

    # Delete lesson
    resp = await client.delete(f"/admin/lessons/{lesson_id}", headers=HEADERS)
    assert resp.status_code == 200

    # Verify lesson count
    resp = await client.get(f"/admin/modules/{module_id}/lessons", headers=HEADERS)
    assert len(resp.json()) == 1

    # Cleanup module
    await client.delete(f"/admin/modules/{module_id}", headers=HEADERS)


async def test_module_reorder(client):
    """Create two modules, reorder them."""
    resp1 = await client.post("/admin/modules", json={
        "topic": "t1", "title": "First", "icon": "1️⃣",
        "order_index": 0, "country_codes": [],
    }, headers=HEADERS)
    id1 = resp1.json()["id"]

    resp2 = await client.post("/admin/modules", json={
        "topic": "t2", "title": "Second", "icon": "2️⃣",
        "order_index": 1, "country_codes": [],
    }, headers=HEADERS)
    id2 = resp2.json()["id"]

    # Swap order
    resp = await client.patch("/admin/modules/reorder", json={
        "order": [
            {"id": id1, "order_index": 1},
            {"id": id2, "order_index": 0},
        ],
    }, headers=HEADERS)
    assert resp.status_code == 200

    # Verify new order
    resp = await client.get("/admin/modules", headers=HEADERS)
    modules = resp.json()
    m1 = next(m for m in modules if m["id"] == id1)
    m2 = next(m for m in modules if m["id"] == id2)
    assert m1["order_index"] == 1
    assert m2["order_index"] == 0

    # Cleanup
    await client.delete(f"/admin/modules/{id1}", headers=HEADERS)
    await client.delete(f"/admin/modules/{id2}", headers=HEADERS)


async def test_lesson_content_validation_rejects_invalid(client):
    """Invalid content_json should return 422."""
    resp = await client.post("/admin/modules", json={
        "topic": "val_test", "title": "Validation Test", "icon": "⚠️",
        "order_index": 0, "country_codes": [],
    }, headers=HEADERS)
    module_id = resp.json()["id"]

    # Card missing body
    resp = await client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "card", "content_json": {"title": "No body"},
        "xp_reward": 10, "order_index": 0,
    }, headers=HEADERS)
    assert resp.status_code == 422

    # Cleanup
    await client.delete(f"/admin/modules/{module_id}", headers=HEADERS)
