"""TDD tests: "keep published" — clear a false-positive verifier flag in place.

The verifier is advisory. When an operator reviews a flagged *approved* item and
judges it correct (a verifier false positive), they need a one-click way to clear
the flag WITHOUT unpublishing — so it drops out of the "needs review" list but
stays live.

Coverage:
- POST /admin/diagnostic-items/{id}/clear-verifier-flag on an approved flagged
  item → 200, all verifier_* None, status STILL approved, approved_by/at unchanged
- on a draft → 409 (drafts clear their flag by editing instead)
- on a retired → 409
- unauth (plain client) → 401/403
- unknown id → 404
- idempotent: approved item with no flag → 200, fields stay None
- the cleared item no longer appears under the verifier=needs_review filter
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.diagnostic import DiagnosticItem

pytestmark = pytest.mark.asyncio(loop_scope="session")

_CLEAR_URL = "/admin/diagnostic-items/{id}/clear-verifier-flag"
_LIST_URL = "/admin/diagnostic-items"


async def _seed(db_session, **kwargs) -> DiagnosticItem:
    defaults = dict(
        market_code="US",
        topic="stocks",
        difficulty_tier=1,
        question="What is a share?",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        explanation="A share is part of a company.",
        status="draft",
        source="generated",
        concept_id=None,
        approved_by=None,
        approved_at=None,
        verifier_status=None,
        verifier_answer_index=None,
        verifier_note=None,
        verified_at=None,
    )
    defaults.update(kwargs)
    row = DiagnosticItem(**defaults)
    db_session.add(row)
    await db_session.flush()
    return row


# --- auth / not-found -------------------------------------------------------


async def test_clear_requires_auth(client):
    resp = await client.post(_CLEAR_URL.format(id=uuid.uuid4()))
    assert resp.status_code in (401, 403)


async def test_clear_unknown_id_is_404(admin_client):
    resp = await admin_client.post(_CLEAR_URL.format(id=uuid.uuid4()))
    assert resp.status_code == 404


# --- wrong state → 409 ------------------------------------------------------


async def test_clear_draft_is_409(admin_client, db_session):
    row = await _seed(db_session, status="draft", verifier_status="mismatch")
    resp = await admin_client.post(_CLEAR_URL.format(id=row.id))
    assert resp.status_code == 409


async def test_clear_retired_is_409(admin_client, db_session):
    row = await _seed(db_session, status="retired", verifier_status="mismatch")
    resp = await admin_client.post(_CLEAR_URL.format(id=row.id))
    assert resp.status_code == 409


# --- happy path: clears flag, stays approved --------------------------------


async def test_clear_approved_flagged_keeps_approved_and_clears_flag(admin_client, db_session):
    approver = uuid.uuid4()
    approved_at = datetime.now(UTC)
    row = await _seed(
        db_session,
        status="approved",
        answer_index=0,
        approved_by=approver,
        approved_at=approved_at,
        verifier_status="mismatch",
        verifier_answer_index=3,
        verifier_note="verifier disagrees",
        verified_at=datetime.now(UTC),
    )
    resp = await admin_client.post(_CLEAR_URL.format(id=row.id))
    assert resp.status_code == 200
    data = resp.json()
    # flag fully cleared
    assert data["verifier_status"] is None
    assert data["verifier_answer_index"] is None
    assert data["verifier_note"] is None
    assert data["verified_at"] is None
    # still published — approval untouched, answer untouched
    assert data["status"] == "approved"
    assert data["approved_by"] == str(approver)
    assert data["approved_at"] is not None
    assert data["answer_index"] == 0


async def test_clear_ambiguous_flag(admin_client, db_session):
    row = await _seed(
        db_session,
        status="approved",
        approved_by=uuid.uuid4(),
        approved_at=datetime.now(UTC),
        verifier_status="ambiguous",
        verifier_answer_index=1,
        verifier_note="two plausible answers",
        verified_at=datetime.now(UTC),
    )
    resp = await admin_client.post(_CLEAR_URL.format(id=row.id))
    assert resp.status_code == 200
    assert resp.json()["verifier_status"] is None


async def test_clear_is_idempotent_when_no_flag(admin_client, db_session):
    """Clearing an approved item that has no flag is a harmless no-op (200)."""
    row = await _seed(
        db_session,
        status="approved",
        approved_by=uuid.uuid4(),
        approved_at=datetime.now(UTC),
    )
    resp = await admin_client.post(_CLEAR_URL.format(id=row.id))
    assert resp.status_code == 200
    assert resp.json()["verifier_status"] is None


# --- dropped from needs_review filter ---------------------------------------


async def test_cleared_item_leaves_needs_review_filter(admin_client, db_session):
    row = await _seed(
        db_session,
        status="approved",
        approved_by=uuid.uuid4(),
        approved_at=datetime.now(UTC),
        verifier_status="mismatch",
        verifier_answer_index=2,
        verifier_note="disagrees",
        verified_at=datetime.now(UTC),
    )
    # present in needs_review before
    resp = await admin_client.get(_LIST_URL, params={"verifier": "needs_review"})
    assert resp.status_code == 200
    ids_before = {i["id"] for i in resp.json()["items"]}
    assert str(row.id) in ids_before

    # clear the flag
    resp = await admin_client.post(_CLEAR_URL.format(id=row.id))
    assert resp.status_code == 200

    # gone from needs_review after
    resp = await admin_client.get(_LIST_URL, params={"verifier": "needs_review"})
    assert resp.status_code == 200
    ids_after = {i["id"] for i in resp.json()["items"]}
    assert str(row.id) not in ids_after
