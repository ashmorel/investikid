"""Task 6 — Admin Concepts API TDD.

Covers:
- Unauth → 401 on all concept admin endpoints.
- Admin can list concepts grouped by topic (with lesson_count + unmapped_count).
- Admin can create a concept.
- Admin can edit a concept (name / blurb / difficulty_tier / order_index / topic).
- Admin can reassign a lesson's concept_id (and clear it).
- lesson_count reflects linked lessons.
- unmapped_count reflects published lessons in a topic with concept_id IS NULL.
"""
import uuid

import pytest

from app.models.concept import Concept
from app.models.content import Lesson, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _concept(**kwargs) -> Concept:
    defaults = dict(
        topic="stocks",
        slug=f"c-{uuid.uuid4().hex[:8]}",
        name="Test Concept",
        blurb="A short blurb.",
        difficulty_tier=1,
        order_index=0,
    )
    return Concept(**{**defaults, **kwargs})


async def _module(db_session, topic="stocks") -> Module:
    m = Module(
        topic=topic, title=f"Mod-{uuid.uuid4().hex[:6]}",
        country_codes=[], is_premium=False, order_index=0, icon="📚",
    )
    db_session.add(m)
    await db_session.flush()
    return m


async def _lesson(db_session, module_id, concept_id=None) -> Lesson:
    lsn = Lesson(
        module_id=module_id,
        type="card",
        content_json={"title": "T", "body": "B"},
        xp_reward=10,
        order_index=0,
        concept_id=concept_id,
    )
    db_session.add(lsn)
    await db_session.flush()
    return lsn


# ---------------------------------------------------------------------------
# Auth guard — unauthenticated requests must get 401
# ---------------------------------------------------------------------------

async def test_list_concepts_unauth(client):
    r = await client.get("/admin/concepts")
    assert r.status_code in (401, 403)


async def test_create_concept_unauth(client):
    r = await client.post("/admin/concepts", json={
        "topic": "stocks", "slug": "unauth-test", "name": "X",
        "difficulty_tier": 1, "order_index": 0,
    })
    assert r.status_code in (401, 403)


async def test_patch_concept_unauth(client):
    r = await client.patch(f"/admin/concepts/{uuid.uuid4()}", json={"name": "Y"})
    assert r.status_code in (401, 403)


async def test_patch_lesson_concept_unauth(client):
    r = await client.patch(f"/admin/lessons/{uuid.uuid4()}/concept", json={"concept_id": None})
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Create concept
# ---------------------------------------------------------------------------

async def test_admin_create_concept(admin_client):
    slug = f"stocks-basics-{uuid.uuid4().hex[:6]}"
    r = await admin_client.post("/admin/concepts", json={
        "topic": "stocks",
        "slug": slug,
        "name": "Stocks Basics",
        "blurb": "Intro to stocks.",
        "difficulty_tier": 1,
        "order_index": 99,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["slug"] == slug
    assert data["name"] == "Stocks Basics"
    assert data["difficulty_tier"] == 1


async def test_admin_create_concept_duplicate_slug_rejected(admin_client):
    slug = f"dup-slug-{uuid.uuid4().hex[:6]}"
    payload = {"topic": "stocks", "slug": slug, "name": "A", "difficulty_tier": 1, "order_index": 0}
    r1 = await admin_client.post("/admin/concepts", json=payload)
    assert r1.status_code == 201
    r2 = await admin_client.post("/admin/concepts", json=payload)
    assert r2.status_code == 409


# ---------------------------------------------------------------------------
# Edit concept
# ---------------------------------------------------------------------------

async def test_admin_edit_concept(admin_client, db_session):
    concept = _concept(slug=f"edit-me-{uuid.uuid4().hex[:6]}")
    db_session.add(concept)
    await db_session.flush()

    r = await admin_client.patch(f"/admin/concepts/{concept.id}", json={
        "name": "Renamed Concept",
        "difficulty_tier": 3,
        "order_index": 5,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "Renamed Concept"
    assert data["difficulty_tier"] == 3


async def test_admin_edit_concept_not_found(admin_client):
    r = await admin_client.patch(f"/admin/concepts/{uuid.uuid4()}", json={"name": "X"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# lesson_count
# ---------------------------------------------------------------------------

async def test_lesson_count_reflects_linked_lessons(admin_client, db_session):
    concept = _concept(slug=f"count-test-{uuid.uuid4().hex[:6]}", topic="savings")
    db_session.add(concept)
    mod = await _module(db_session, topic="savings")
    await db_session.flush()
    await _lesson(db_session, mod.id, concept_id=concept.id)
    await _lesson(db_session, mod.id, concept_id=concept.id)
    await db_session.commit()

    r = await admin_client.get("/admin/concepts")
    assert r.status_code == 200
    groups = r.json()
    savings_group = next((g for g in groups if g["topic"] == "savings"), None)
    assert savings_group is not None
    matched = [c for c in savings_group["concepts"] if c["id"] == str(concept.id)]
    assert matched, "Concept not found in response"
    assert matched[0]["lesson_count"] >= 2


# ---------------------------------------------------------------------------
# unmapped_count
# ---------------------------------------------------------------------------

async def test_unmapped_count_reflects_null_concept_lessons(admin_client, db_session):
    # Create a module in "budgeting" topic with 3 lessons, 2 unmapped (NULL concept_id)
    # and 1 mapped.
    concept = _concept(slug=f"budg-{uuid.uuid4().hex[:6]}", topic="budgeting")
    db_session.add(concept)
    mod = await _module(db_session, topic="budgeting")
    await db_session.flush()
    # 2 unmapped lessons
    await _lesson(db_session, mod.id, concept_id=None)
    await _lesson(db_session, mod.id, concept_id=None)
    # 1 mapped lesson
    await _lesson(db_session, mod.id, concept_id=concept.id)
    await db_session.commit()

    r = await admin_client.get("/admin/concepts")
    assert r.status_code == 200
    groups = r.json()
    budg_group = next((g for g in groups if g["topic"] == "budgeting"), None)
    assert budg_group is not None
    # unmapped_count should be >= 2 (may include other tests' data)
    assert budg_group["unmapped_count"] >= 2


# ---------------------------------------------------------------------------
# Reassign lesson concept
# ---------------------------------------------------------------------------

async def test_admin_reassign_lesson_concept(admin_client, db_session):
    concept = _concept(slug=f"reassign-{uuid.uuid4().hex[:6]}", topic="risk")
    db_session.add(concept)
    mod = await _module(db_session, topic="risk")
    await db_session.flush()
    lesson = await _lesson(db_session, mod.id, concept_id=None)
    await db_session.commit()

    r = await admin_client.patch(f"/admin/lessons/{lesson.id}/concept", json={
        "concept_id": str(concept.id),
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["concept_id"] == str(concept.id)


async def test_admin_clear_lesson_concept(admin_client, db_session):
    concept = _concept(slug=f"clear-{uuid.uuid4().hex[:6]}", topic="debt")
    db_session.add(concept)
    mod = await _module(db_session, topic="debt")
    await db_session.flush()
    lesson = await _lesson(db_session, mod.id, concept_id=concept.id)
    await db_session.commit()

    r = await admin_client.patch(f"/admin/lessons/{lesson.id}/concept", json={
        "concept_id": None,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["concept_id"] is None


async def test_admin_reassign_lesson_invalid_concept(admin_client, db_session):
    mod = await _module(db_session, topic="taxes")
    await db_session.flush()
    lesson = await _lesson(db_session, mod.id, concept_id=None)
    await db_session.commit()

    r = await admin_client.patch(f"/admin/lessons/{lesson.id}/concept", json={
        "concept_id": str(uuid.uuid4()),
    })
    assert r.status_code == 404


async def test_admin_reassign_lesson_not_found(admin_client):
    r = await admin_client.patch(f"/admin/lessons/{uuid.uuid4()}/concept", json={
        "concept_id": None,
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# VALID_TOPICS enforcement
# ---------------------------------------------------------------------------

async def test_create_concept_invalid_topic_rejected(admin_client):
    """POST /admin/concepts with an unknown topic must return 422 (not persisted)."""
    r = await admin_client.post("/admin/concepts", json={
        "topic": "nonsense",
        "slug": f"invalid-topic-{uuid.uuid4().hex[:6]}",
        "name": "Bad Topic Concept",
        "difficulty_tier": 1,
        "order_index": 0,
    })
    assert r.status_code == 422


async def test_patch_concept_invalid_topic_rejected(admin_client, db_session):
    """PATCH /admin/concepts/{id} with an unknown topic must return 422."""
    concept = _concept(slug=f"valid-topic-patch-{uuid.uuid4().hex[:6]}")
    db_session.add(concept)
    await db_session.commit()

    r = await admin_client.patch(f"/admin/concepts/{concept.id}", json={
        "topic": "nonsense",
    })
    assert r.status_code == 422


async def test_create_concept_valid_topic_accepted(admin_client):
    """POST /admin/concepts with a valid topic must succeed (200-level)."""
    r = await admin_client.post("/admin/concepts", json={
        "topic": "crypto",
        "slug": f"crypto-intro-{uuid.uuid4().hex[:6]}",
        "name": "Crypto Intro",
        "difficulty_tier": 2,
        "order_index": 1,
    })
    assert r.status_code == 201, r.text


async def test_patch_concept_omitting_topic_accepted(admin_client, db_session):
    """PATCH /admin/concepts/{id} without a topic field must still succeed."""
    concept = _concept(slug=f"no-topic-patch-{uuid.uuid4().hex[:6]}")
    db_session.add(concept)
    await db_session.commit()

    r = await admin_client.patch(f"/admin/concepts/{concept.id}", json={
        "name": "Renamed Without Topic Change",
    })
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Renamed Without Topic Change"
