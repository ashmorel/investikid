"""Admin word-bank API tests (Task 7).

Mirrors test_video_curation_api.py: seeds an ArcadeWord via db_session,
exercises the four admin endpoints, and asserts expected outcomes.
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.arcade_word import ArcadeWord

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _pending_word(db_session, *, word: str = "BUDGET") -> ArcadeWord:
    w = ArcadeWord(
        word=word,
        definition="A plan for how to spend your money each month.",
        language="en",
        length=len(word),
        status="pending",
        source="llm",
    )
    db_session.add(w)
    await db_session.flush()
    return w


# ── List ──────────────────────────────────────────────────────────────


async def test_list_pending(admin_client, db_session):
    w = await _pending_word(db_session)
    r = await admin_client.get("/admin/arcade-words?status=pending")
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()]
    assert str(w.id) in ids


async def test_list_filters_by_language(admin_client, db_session):
    w = await _pending_word(db_session, word="INVEST")
    r = await admin_client.get("/admin/arcade-words?status=pending&language=fr")
    assert r.status_code == 200
    ids = [item["id"] for item in r.json()]
    # The word we added is "en", so it should NOT appear when filtering for "fr"
    assert str(w.id) not in ids


# ── Approve ───────────────────────────────────────────────────────────


async def test_approve_flips_status(admin_client, db_session):
    w = await _pending_word(db_session, word="DEBIT")
    r = await admin_client.post(f"/admin/arcade-words/{w.id}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    await db_session.refresh(w)
    assert w.status == "approved"


async def test_approve_with_edit(admin_client, db_session):
    w = await _pending_word(db_session, word="CREDIT")
    r = await admin_client.post(
        f"/admin/arcade-words/{w.id}/approve",
        json={"definition": "Money borrowed from a bank that must be paid back."},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved"
    assert data["definition"] == "Money borrowed from a bank that must be paid back."


async def test_approve_edit_overlength_definition_422(admin_client, db_session):
    w = await _pending_word(db_session, word="GRANT")
    # 181-char definition — must fail validation
    bad_def = "A" * 181
    r = await admin_client.post(
        f"/admin/arcade-words/{w.id}/approve",
        json={"definition": bad_def},
    )
    assert r.status_code == 422
    # status must remain pending
    await db_session.refresh(w)
    assert w.status == "pending"


async def test_approve_edit_invalid_word_422(admin_client, db_session):
    w = await _pending_word(db_session, word="ASSET")
    # Word with digits — invalid
    r = await admin_client.post(
        f"/admin/arcade-words/{w.id}/approve",
        json={"word": "ASSET1"},
    )
    assert r.status_code == 422


async def test_approve_not_found_404(admin_client, db_session):
    r = await admin_client.post(f"/admin/arcade-words/{uuid.uuid4()}/approve")
    assert r.status_code == 404


# ── Reject ────────────────────────────────────────────────────────────


async def test_reject_flips_status(admin_client, db_session):
    w = await _pending_word(db_session, word="EQUITY")
    r = await admin_client.post(f"/admin/arcade-words/{w.id}/reject")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
    await db_session.refresh(w)
    assert w.status == "rejected"


async def test_reject_not_found_404(admin_client, db_session):
    r = await admin_client.post(f"/admin/arcade-words/{uuid.uuid4()}/reject")
    assert r.status_code == 404


# ── Suggest (auth + wiring) ───────────────────────────────────────────


async def test_suggest_requires_admin(client):
    """Non-admin (no auth) gets 401/403."""
    r = await client.post("/admin/arcade-words/suggest", json={})
    assert r.status_code in (401, 403)


async def test_suggest_wired(admin_client):
    """Admin call reaches the service; we monkeypatch to avoid LLM I/O."""
    with patch(
        "app.routers.arcade_words_admin.suggest_words",
        new=AsyncMock(return_value={"created": 3, "skipped": 1}),
    ):
        r = await admin_client.post("/admin/arcade-words/suggest", json={"count": 3})
    assert r.status_code == 200
    assert r.json() == {"created": 3, "skipped": 1}
