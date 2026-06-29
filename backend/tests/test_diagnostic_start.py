"""Tests for POST /diagnostic/start (Task 2 — item selection + start).

TDD: tests written first, run → fail, then implementation lands.

Coverage:
- approved-only: draft + retired items excluded; only approved items returned
- no answer_index / explanation in response payload (server-authoritative scoring)
- times_shown bumped for every selected item; DiagnosticSession row created
- unseen-first: prior completed session's item ids are de-prioritised
- empty path: zero approved items → session with item_ids=[], no error
- topic_path: a 4th topic beyond the 3 defaults is included when set
- unauth (plain client) → 401 / 403
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.diagnostic import DiagnosticItem
from app.models.mastery import DiagnosticSession
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_MARKET = "GB"


def _make_item(
    db_session,
    *,
    topic: str = "budgeting",
    difficulty_tier: int = 1,
    market_code: str = _DEFAULT_MARKET,
    status: str = "approved",
) -> DiagnosticItem:
    item = DiagnosticItem(
        market_code=market_code,
        topic=topic,
        difficulty_tier=difficulty_tier,
        question=f"What is {topic}? (tier {difficulty_tier})",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        explanation="Because reasons.",
        status=status,
        source="authored",
    )
    db_session.add(item)
    return item


async def _seed_item(db_session, **kwargs) -> DiagnosticItem:
    item = _make_item(db_session, **kwargs)
    await db_session.flush()
    return item


async def _login(client, email: str, password: str) -> None:
    await client.post("/auth/login", json={"email": email, "password": password})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _register_and_login(client, db_session, *, suffix: str = "") -> User:
    """Register a new user, log them in, return the ORM User row."""
    from sqlalchemy import select

    email = f"diag{suffix}@example.com"
    username = f"diagkid{suffix}"
    payload = {
        "email": email,
        "username": username,
        "password": "SecurePass123!",
        "dob": "2012-01-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": f"parent{suffix}@example.com",
    }
    await client.post("/auth/register", json=payload)
    await _login(client, email, "SecurePass123!")
    return await db_session.scalar(select(User).where(User.username == username))


# ---------------------------------------------------------------------------
# Unauth
# ---------------------------------------------------------------------------


async def test_start_requires_auth(client):
    resp = await client.post("/diagnostic/start")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Basic: only approved items returned; no answer_index / explanation
# ---------------------------------------------------------------------------


async def test_start_returns_only_approved_items(client, db_session):
    await _register_and_login(client, db_session, suffix="_appr")

    # Seed approved items for the 3 default topics
    approved = []
    for topic in ("budgeting", "savings", "risk"):
        approved.append(await _seed_item(db_session, topic=topic, difficulty_tier=1))

    # Seed draft + retired items that must NOT appear
    await _seed_item(db_session, topic="budgeting", status="draft")
    await _seed_item(db_session, topic="savings", status="retired")

    resp = await client.post("/diagnostic/start")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "items" in data
    returned_ids = {i["id"] for i in data["items"]}

    # All returned ids must be from the approved set
    approved_ids = {str(a.id) for a in approved}
    assert returned_ids.issubset(approved_ids)


async def test_start_no_answer_index_in_payload(client, db_session):
    await _register_and_login(client, db_session, suffix="_noans")

    for topic in ("budgeting", "savings", "risk"):
        await _seed_item(db_session, topic=topic, difficulty_tier=1)

    resp = await client.post("/diagnostic/start")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "answer_index" not in item
        assert "explanation" not in item


# ---------------------------------------------------------------------------
# times_shown bump + session row
# ---------------------------------------------------------------------------


async def test_start_bumps_times_shown_and_creates_session(client, db_session):
    user = await _register_and_login(client, db_session, suffix="_bump")

    item_bud = await _seed_item(db_session, topic="budgeting", difficulty_tier=1)
    item_sav = await _seed_item(db_session, topic="savings", difficulty_tier=2)
    item_risk = await _seed_item(db_session, topic="risk", difficulty_tier=1)

    before_shown = {
        item_bud.id: item_bud.times_shown,
        item_sav.id: item_sav.times_shown,
        item_risk.id: item_risk.times_shown,
    }

    resp = await client.post("/diagnostic/start")
    assert resp.status_code == 200
    session_id = uuid.UUID(resp.json()["session_id"])

    # Refresh from DB
    await db_session.refresh(item_bud)
    await db_session.refresh(item_sav)
    await db_session.refresh(item_risk)

    returned_ids = {i["id"] for i in resp.json()["items"]}
    for item in (item_bud, item_sav, item_risk):
        if str(item.id) in returned_ids:
            assert item.times_shown == before_shown[item.id] + 1

    # Session row created with matching item_ids
    diag_session = await db_session.get(DiagnosticSession, session_id)
    assert diag_session is not None
    assert diag_session.user_id == user.id
    assert set(diag_session.item_ids) == returned_ids


# ---------------------------------------------------------------------------
# Unseen-first: prior session's items are de-prioritised
# ---------------------------------------------------------------------------


async def test_start_prefers_unseen_items(client, db_session):
    user = await _register_and_login(client, db_session, suffix="_unseen")

    # Seed 4 approved budgeting items (2 seen, 2 unseen)
    seen_1 = await _seed_item(db_session, topic="budgeting", difficulty_tier=1)
    seen_2 = await _seed_item(db_session, topic="budgeting", difficulty_tier=2)
    unseen_1 = await _seed_item(db_session, topic="budgeting", difficulty_tier=3)
    unseen_2 = await _seed_item(db_session, topic="budgeting", difficulty_tier=1)

    # Create a prior completed session that includes seen_1 + seen_2
    prior = DiagnosticSession(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind="baseline",
        item_ids=[str(seen_1.id), str(seen_2.id)],
        completed_at=datetime.now(UTC),
    )
    db_session.add(prior)
    await db_session.flush()

    # Also seed 1 item each for savings and risk so we have valid in-scope topics
    await _seed_item(db_session, topic="savings", difficulty_tier=1)
    await _seed_item(db_session, topic="risk", difficulty_tier=1)

    resp = await client.post("/diagnostic/start")
    assert resp.status_code == 200
    returned_ids = {i["id"] for i in resp.json()["items"]}

    budgeting_returned = {str(seen_1.id), str(seen_2.id), str(unseen_1.id), str(unseen_2.id)} & returned_ids
    # When unseen items exist, the seen items should NOT be chosen (we have 2 unseen, cap is 2)
    assert str(unseen_1.id) in budgeting_returned or str(unseen_2.id) in budgeting_returned
    # Neither seen_1 nor seen_2 should appear when 2 unseen alternatives are available
    assert str(seen_1.id) not in budgeting_returned
    assert str(seen_2.id) not in budgeting_returned


# ---------------------------------------------------------------------------
# Empty path: zero approved items → session with item_ids=[], no crash
# ---------------------------------------------------------------------------


async def test_start_empty_path_no_approved_items(client, db_session):
    """With no approved items in scope, start must return {session_id, items: []} without crashing."""
    await _register_and_login(client, db_session, suffix="_empty")

    # Seed only draft / retired items — no approved
    await _seed_item(db_session, topic="budgeting", status="draft")
    await _seed_item(db_session, topic="savings", status="retired")

    resp = await client.post("/diagnostic/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert "session_id" in data

    # Session row exists with empty item_ids
    session_id = uuid.UUID(data["session_id"])
    diag_session = await db_session.get(DiagnosticSession, session_id)
    assert diag_session is not None
    assert diag_session.item_ids == []


# ---------------------------------------------------------------------------
# topic_path: 4th topic included when set
# ---------------------------------------------------------------------------


async def test_start_includes_topic_path_topic(client, db_session):
    user = await _register_and_login(client, db_session, suffix="_tpath")

    # Give user a topic_path pointing to "stocks"
    user.topic_path = "stocks"
    await db_session.flush()

    # Seed approved items for default 3 topics + stocks
    for topic in ("budgeting", "savings", "risk", "stocks"):
        await _seed_item(db_session, topic=topic, difficulty_tier=1)

    resp = await client.post("/diagnostic/start")
    assert resp.status_code == 200

    topics_returned = {i["topic"] for i in resp.json()["items"]}
    assert "stocks" in topics_returned


# ---------------------------------------------------------------------------
# Abandoned session: items from incomplete sessions remain eligible (unseen)
# ---------------------------------------------------------------------------


async def test_abandoned_session_items_remain_eligible(client, db_session):
    """Items in an abandoned (completed_at=None) session must NOT be treated as
    seen — they should be preferred as unseen on the next start, exactly like
    items that have never been shown at all.

    Setup: 4 budgeting items.
      - item_c / item_d are in a prior *completed* session → truly seen.
      - item_a / item_b are in an *abandoned* session (completed_at=None) →
        must be treated as unseen.

    With _ITEMS_PER_TOPIC=2 the service should pick item_a+item_b (unseen)
    over item_c+item_d (seen via completed session).  Under the buggy code
    _seen_item_ids returns all four, leaving an empty unseen pool and forcing
    the fallback to seen items — meaning item_a/item_b could be skipped even
    though they were never actually completed.
    """
    user = await _register_and_login(client, db_session, suffix="_aband")

    # Items that belong to the completed session — truly seen, should be de-prioritised.
    # Created FIRST so they sort earliest by created_at (stable ordering).
    item_c = await _seed_item(db_session, topic="budgeting", difficulty_tier=1)
    item_d = await _seed_item(db_session, topic="budgeting", difficulty_tier=1)

    # Items that belong to the abandoned session — must be treated as unseen.
    # Created AFTER so they sort later; if wrongly treated as seen they lose to item_c/d.
    item_a = await _seed_item(db_session, topic="budgeting", difficulty_tier=1)
    item_b = await _seed_item(db_session, topic="budgeting", difficulty_tier=1)

    # Completed session: item_c + item_d are genuinely seen
    completed = DiagnosticSession(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind="baseline",
        item_ids=[str(item_c.id), str(item_d.id)],
        completed_at=datetime.now(UTC),
    )
    db_session.add(completed)

    # Abandoned session: item_a + item_b were started but never submitted
    abandoned = DiagnosticSession(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind="baseline",
        item_ids=[str(item_a.id), str(item_b.id)],
        completed_at=None,  # NOT completed — abandoned mid-session
    )
    db_session.add(abandoned)
    await db_session.flush()

    # Seed 1 item each for savings and risk to satisfy in-scope topics
    await _seed_item(db_session, topic="savings", difficulty_tier=1)
    await _seed_item(db_session, topic="risk", difficulty_tier=1)

    resp = await client.post("/diagnostic/start")
    assert resp.status_code == 200
    returned_ids = {i["id"] for i in resp.json()["items"]}

    budgeting_returned = {
        str(item_a.id), str(item_b.id), str(item_c.id), str(item_d.id)
    } & returned_ids

    # item_a and item_b are unseen (abandoned session doesn't count) so they
    # must be preferred — both should appear in the 2-item budgeting slot.
    assert str(item_a.id) in budgeting_returned, (
        "item_a (in abandoned session) was wrongly excluded — abandoned sessions "
        "must not contribute to the seen set"
    )
    assert str(item_b.id) in budgeting_returned, (
        "item_b (in abandoned session) was wrongly excluded — abandoned sessions "
        "must not contribute to the seen set"
    )
    # item_c and item_d are truly seen (completed session) — must NOT appear
    assert str(item_c.id) not in budgeting_returned, (
        "item_c (in completed session) should be de-prioritised when unseen items exist"
    )
    assert str(item_d.id) not in budgeting_returned, (
        "item_d (in completed session) should be de-prioritised when unseen items exist"
    )
