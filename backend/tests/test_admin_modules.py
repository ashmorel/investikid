import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_modules_requires_auth(client):
    """Unauthenticated request to a moved content route must be rejected (not 200)."""
    resp = await client.get("/admin/modules")
    assert resp.status_code in (401, 403)

async def test_module_crud_lifecycle(admin_client):
    """Create → read → update → reorder → delete a module."""
    # Create
    resp = await admin_client.post("/admin/modules", json={
        "topic": "test_topic", "title": "Test Module", "icon": "🧪",
        "is_premium": False, "country_codes": [], "order_index": 0,
    })
    assert resp.status_code == 200
    module = resp.json()
    module_id = module["id"]
    assert module["topic"] == "test_topic"
    assert module["lesson_count"] == 0

    # List
    resp = await admin_client.get("/admin/modules")
    assert resp.status_code == 200
    modules = resp.json()
    assert any(m["id"] == module_id for m in modules)

    # Update
    resp = await admin_client.put(f"/admin/modules/{module_id}", json={
        "title": "Updated Module",
    })
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Module"

    # Delete — a freshly-created module is published (live), so archiving is
    # refused; you must unpublish/replace it first (see test_module_archive for
    # the non-live soft-archive + restore path).
    resp = await admin_client.delete(f"/admin/modules/{module_id}")
    assert resp.status_code == 409

    # Still present (not archived)
    resp = await admin_client.get("/admin/modules")
    assert any(m["id"] == module_id for m in resp.json())


async def test_lesson_crud_lifecycle(admin_client):
    """Create module → add lessons → reorder → update → delete."""
    # Create module first
    resp = await admin_client.post("/admin/modules", json={
        "topic": "lessons_test", "title": "Lesson Test Module", "icon": "📝",
        "is_premium": False, "country_codes": [], "order_index": 0,
    })
    module_id = resp.json()["id"]

    # Create card lesson
    resp = await admin_client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "card",
        "content_json": {"title": "Card Title", "body": "Card body"},
        "xp_reward": 10, "order_index": 0,
    })
    assert resp.status_code == 200
    lesson_id = resp.json()["id"]
    assert resp.json()["type"] == "card"

    # Create quiz lesson
    resp = await admin_client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "quiz",
        "content_json": {
            "question": "Q?", "choices": ["A", "B"],
            "answer_index": 0, "explanation": "Because A",
        },
        "xp_reward": 25, "order_index": 1,
    })
    assert resp.status_code == 200

    # List lessons
    resp = await admin_client.get(f"/admin/modules/{module_id}/lessons")
    assert len(resp.json()) == 2

    # Update lesson
    resp = await admin_client.put(f"/admin/lessons/{lesson_id}", json={
        "content_json": {"title": "Updated Card", "body": "Updated body"},
    })
    assert resp.status_code == 200
    assert resp.json()["content_json"]["title"] == "Updated Card"

    # Delete lesson
    resp = await admin_client.delete(f"/admin/lessons/{lesson_id}")
    assert resp.status_code == 200

    # Verify lesson count
    resp = await admin_client.get(f"/admin/modules/{module_id}/lessons")
    assert len(resp.json()) == 1

    # Cleanup module
    await admin_client.delete(f"/admin/modules/{module_id}")


async def test_module_reorder(admin_client):
    """Create two modules, reorder them."""
    resp1 = await admin_client.post("/admin/modules", json={
        "topic": "t1", "title": "First", "icon": "1️⃣",
        "order_index": 0, "country_codes": [],
    })
    id1 = resp1.json()["id"]

    resp2 = await admin_client.post("/admin/modules", json={
        "topic": "t2", "title": "Second", "icon": "2️⃣",
        "order_index": 1, "country_codes": [],
    })
    id2 = resp2.json()["id"]

    # Swap order
    resp = await admin_client.patch("/admin/modules/reorder", json={
        "order": [
            {"id": id1, "order_index": 1},
            {"id": id2, "order_index": 0},
        ],
    })
    assert resp.status_code == 200

    # Verify new order
    resp = await admin_client.get("/admin/modules")
    modules = resp.json()
    m1 = next(m for m in modules if m["id"] == id1)
    m2 = next(m for m in modules if m["id"] == id2)
    assert m1["order_index"] == 1
    assert m2["order_index"] == 0

    # Cleanup
    await admin_client.delete(f"/admin/modules/{id1}")
    await admin_client.delete(f"/admin/modules/{id2}")


async def test_lesson_content_validation_rejects_invalid(admin_client):
    """Invalid content_json should return 422."""
    resp = await admin_client.post("/admin/modules", json={
        "topic": "val_test", "title": "Validation Test", "icon": "⚠️",
        "order_index": 0, "country_codes": [],
    })
    module_id = resp.json()["id"]

    # Card missing body
    resp = await admin_client.post(f"/admin/modules/{module_id}/lessons", json={
        "type": "card", "content_json": {"title": "No body"},
        "xp_reward": 10, "order_index": 0,
    })
    assert resp.status_code == 422

    # Cleanup
    await admin_client.delete(f"/admin/modules/{module_id}")


async def test_module_update_standards_and_sources(admin_client):
    resp = await admin_client.post("/admin/modules", json={
        "topic": "stocks", "title": "Cred Module", "icon": "🏛️",
        "is_premium": False, "country_codes": [], "order_index": 0,
    })
    module_id = resp.json()["id"]

    standards = [{"framework": "Jump$tart", "code": "SI-1", "label": "Saving & Investing 1"}]
    sources = [{"title": "Bank of England explainer",
                "url": "https://www.bankofengland.co.uk/explainers"}]
    resp = await admin_client.put(f"/admin/modules/{module_id}", json={
        "standards_alignment": standards, "sources": sources,
    })
    assert resp.status_code == 200
    assert resp.json()["standards_alignment"] == standards
    assert resp.json()["sources"] == sources

    # Persists — visible on the admin list too
    resp = await admin_client.get("/admin/modules")
    mod = next(m for m in resp.json() if m["id"] == module_id)
    assert mod["standards_alignment"] == standards
    assert mod["sources"] == sources


async def test_module_update_rejects_bad_source_url(admin_client):
    resp = await admin_client.post("/admin/modules", json={
        "topic": "stocks", "title": "Bad URL Module", "icon": "🏛️",
        "is_premium": False, "country_codes": [], "order_index": 0,
    })
    module_id = resp.json()["id"]

    resp = await admin_client.put(f"/admin/modules/{module_id}", json={
        "sources": [{"title": "Sketchy", "url": "javascript:alert(1)"}],
    })
    assert resp.status_code == 422
