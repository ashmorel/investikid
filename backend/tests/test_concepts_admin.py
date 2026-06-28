"""Task 6 → A1.2 Task 2 — Admin Concepts API TDD.

Covers:
- Unauth → 401 on all concept admin endpoints.
- Admin can list concepts: response has top-level unmapped_lessons (global) + groups list.
- Admin can create a concept.
- Admin can edit a concept (name / blurb / difficulty_tier / order_index / topic).
- Admin can reassign a lesson's concept_id (and clear it).
- lesson_count reflects linked lessons.
- unmapped_lessons = count of published lessons (across ALL topics) with concept_id IS NULL.
- unmapped_lessons excludes unpublished-module lessons.
- unmapped_lessons excludes tagged (concept_id IS NOT NULL) lessons.
"""
import uuid

import pytest
from sqlalchemy import func
from sqlalchemy import select as sa_select

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
    body = r.json()
    groups = body["groups"]
    savings_group = next((g for g in groups if g["topic"] == "savings"), None)
    assert savings_group is not None
    matched = [c for c in savings_group["concepts"] if c["id"] == str(concept.id)]
    assert matched, "Concept not found in response"
    assert matched[0]["lesson_count"] >= 2


# ---------------------------------------------------------------------------
# unmapped_lessons (global, top-level)
# ---------------------------------------------------------------------------

async def test_list_concepts_response_shape(admin_client):
    """GET /admin/concepts returns {unmapped_lessons: int, groups: [...]}."""
    r = await admin_client.get("/admin/concepts")
    assert r.status_code == 200
    body = r.json()
    assert "unmapped_lessons" in body, "top-level unmapped_lessons key missing"
    assert "groups" in body, "top-level groups key missing"
    assert isinstance(body["unmapped_lessons"], int)
    assert isinstance(body["groups"], list)
    # TopicGroup must NOT have unmapped_count
    for g in body["groups"]:
        assert "unmapped_count" not in g, "per-topic unmapped_count must be removed"


async def test_unmapped_lessons_counts_published_null_concept_globally(admin_client, db_session):
    """unmapped_lessons reflects published lessons with NULL concept_id across all topics."""
    # Published module with 2 unmapped + 1 tagged lessons
    concept = _concept(slug=f"budg-{uuid.uuid4().hex[:6]}", topic="budgeting")
    db_session.add(concept)
    pub_mod = Module(
        topic="budgeting",
        title=f"PubBudg-{uuid.uuid4().hex[:6]}",
        country_codes=[], is_premium=False, order_index=0, icon="📚",
        published=True,
    )
    db_session.add(pub_mod)
    await db_session.flush()
    await _lesson(db_session, pub_mod.id, concept_id=None)
    await _lesson(db_session, pub_mod.id, concept_id=None)
    await _lesson(db_session, pub_mod.id, concept_id=concept.id)

    # Unpublished module with 1 unmapped lesson — must NOT be counted
    draft_mod = Module(
        topic="budgeting",
        title=f"DraftBudg-{uuid.uuid4().hex[:6]}",
        country_codes=[], is_premium=False, order_index=1, icon="📚",
        published=False,
    )
    db_session.add(draft_mod)
    await db_session.flush()
    await _lesson(db_session, draft_mod.id, concept_id=None)
    await db_session.commit()

    # Get the actual published+null count from the DB for a precise assertion
    published_null = await db_session.scalar(
        sa_select(func.count())
        .select_from(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.published.is_(True), Lesson.concept_id.is_(None))
    )

    r = await admin_client.get("/admin/concepts")
    assert r.status_code == 200
    body = r.json()
    assert body["unmapped_lessons"] == published_null, (
        f"unmapped_lessons {body['unmapped_lessons']} != DB count {published_null}"
    )


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


# ---------------------------------------------------------------------------
# A1.2 Task 2 — unmapped_lessons excludes unpublished-module lessons (global)
# ---------------------------------------------------------------------------

async def test_unmapped_lessons_excludes_unpublished_module_lessons(admin_client, db_session):
    """Unpublished modules' untagged lessons must NOT be included in the global
    unmapped_lessons figure — it must match the DB count of published-only null-concept
    lessons across ALL topics."""
    # Published module with 1 unmapped lesson
    pub_mod = Module(
        topic="entrepreneurship",
        title=f"EntPub-{uuid.uuid4().hex[:6]}",
        country_codes=[], is_premium=False, order_index=0, icon="📚",
        published=True,
    )
    db_session.add(pub_mod)
    await db_session.flush()
    pub_lesson = Lesson(
        module_id=pub_mod.id, type="card",
        content_json={"title": "T", "body": "B"},
        xp_reward=10, order_index=0, concept_id=None,
    )
    db_session.add(pub_lesson)

    # Unpublished module with 1 unmapped lesson — must NOT be counted.
    draft_mod = Module(
        topic="entrepreneurship",
        title=f"EntDraft-{uuid.uuid4().hex[:6]}",
        country_codes=[], is_premium=False, order_index=1, icon="📚",
        published=False,
    )
    db_session.add(draft_mod)
    await db_session.flush()
    draft_lesson = Lesson(
        module_id=draft_mod.id, type="card",
        content_json={"title": "T", "body": "B"},
        xp_reward=10, order_index=0, concept_id=None,
    )
    db_session.add(draft_lesson)
    await db_session.commit()

    # Compute expected from DB (global, published only)
    published_raw = await db_session.scalar(
        sa_select(func.count())
        .select_from(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.published.is_(True), Lesson.concept_id.is_(None))
    )
    total_raw = await db_session.scalar(
        sa_select(func.count())
        .select_from(Lesson)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.concept_id.is_(None))
    )

    r = await admin_client.get("/admin/concepts")
    assert r.status_code == 200
    body = r.json()
    assert body["unmapped_lessons"] == published_raw, (
        f"unmapped_lessons {body['unmapped_lessons']} != published_raw {published_raw}; "
        f"total_including_drafts={total_raw}"
    )
    assert total_raw > published_raw, "test setup error: draft lesson should inflate total"
