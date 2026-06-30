"""TDD tests for Task 1: unpublish endpoint + verifier-clear on patch.

Step 1 (tests first, run to fail, then implement):

Coverage:
- POST /admin/diagnostic-items/{id}/unpublish on an approved item → 200,
  status="draft", approved_by=None, approved_at=None
- unpublish a draft → 409
- unpublish a retired → 409
- unauth (plain client) → 401/403
- unknown id → 404
- PATCH on a draft that changes a content field clears verifier_* fields
- End-to-end: approved+mismatch → unpublish → patch → approve → approved,
  verifier_status is None
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.diagnostic import DiagnosticItem

pytestmark = pytest.mark.asyncio(loop_scope="session")

_UNPUBLISH_URL = "/admin/diagnostic-items/{id}/unpublish"
_PATCH_URL = "/admin/diagnostic-items/{id}"
_APPROVE_URL = "/admin/diagnostic-items/{id}/approve"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# unauth tests
# ---------------------------------------------------------------------------


async def test_unpublish_requires_auth(client):
    resp = await client.post(_UNPUBLISH_URL.format(id=uuid.uuid4()))
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# unpublish: unknown id → 404
# ---------------------------------------------------------------------------


async def test_unpublish_unknown_id_is_404(admin_client):
    resp = await admin_client.post(_UNPUBLISH_URL.format(id=uuid.uuid4()))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# unpublish: wrong state → 409
# ---------------------------------------------------------------------------


async def test_unpublish_draft_is_409(admin_client, db_session):
    row = await _seed(db_session, status="draft")
    resp = await admin_client.post(_UNPUBLISH_URL.format(id=row.id))
    assert resp.status_code == 409


async def test_unpublish_retired_is_409(admin_client, db_session):
    row = await _seed(db_session, status="retired")
    resp = await admin_client.post(_UNPUBLISH_URL.format(id=row.id))
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# unpublish: approved → draft (happy path)
# ---------------------------------------------------------------------------


async def test_unpublish_approved_returns_draft(admin_client, db_session):
    """Unpublishing an approved item → status=draft, approved_by/approved_at cleared."""
    row = await _seed(
        db_session,
        status="approved",
        approved_by=uuid.uuid4(),
        approved_at=datetime.now(UTC),
    )
    resp = await admin_client.post(_UNPUBLISH_URL.format(id=row.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["approved_by"] is None
    assert data["approved_at"] is None


# ---------------------------------------------------------------------------
# patch clears verifier fields when content changes
# ---------------------------------------------------------------------------


async def test_patch_answer_index_clears_verifier_fields(admin_client, db_session):
    """PATCH on a draft that changes answer_index must reset all verifier_* to None."""
    row = await _seed(
        db_session,
        status="draft",
        answer_index=0,
        verifier_status="mismatch",
        verifier_answer_index=3,
        verifier_note="disagrees",
        verified_at=datetime.now(UTC),
    )
    resp = await admin_client.patch(
        _PATCH_URL.format(id=row.id),
        json={"answer_index": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verifier_status"] is None
    assert data["verifier_answer_index"] is None
    assert data["verifier_note"] is None
    assert data["verified_at"] is None


async def test_patch_question_clears_verifier_fields(admin_client, db_session):
    """PATCH on a draft that changes question must reset all verifier_* to None."""
    row = await _seed(
        db_session,
        status="draft",
        verifier_status="agree",
        verifier_answer_index=0,
        verifier_note="correct",
        verified_at=datetime.now(UTC),
    )
    resp = await admin_client.patch(
        _PATCH_URL.format(id=row.id),
        json={"question": "New revised question text?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verifier_status"] is None
    assert data["verifier_answer_index"] is None
    assert data["verifier_note"] is None
    assert data["verified_at"] is None


# ---------------------------------------------------------------------------
# End-to-end: approved+mismatch → unpublish → patch → approve → clean
# ---------------------------------------------------------------------------


async def test_e2e_unpublish_fix_reapprove(admin_client, db_session):
    """Full fix flow:
    1. Seed an approved item with verifier_status="mismatch".
    2. Unpublish → draft, approved fields cleared.
    3. Patch corrected answer_index → verifier_* all None.
    4. Approve → approved with verifier_status=None (no longer needs_review).
    """
    # 1. Approved + mismatch flagged
    row = await _seed(
        db_session,
        status="approved",
        answer_index=0,
        approved_by=uuid.uuid4(),
        approved_at=datetime.now(UTC),
        verifier_status="mismatch",
        verifier_answer_index=2,
        verifier_note="verifier disagrees",
        verified_at=datetime.now(UTC),
    )
    item_url_base = f"/admin/diagnostic-items/{row.id}"

    # 2. Unpublish → draft
    resp = await admin_client.post(f"{item_url_base}/unpublish")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["approved_by"] is None
    assert data["approved_at"] is None
    # verifier fields are preserved at unpublish time (cleared by the edit)
    assert data["verifier_status"] == "mismatch"

    # 3. Patch corrected answer_index → verifier_* cleared
    resp = await admin_client.patch(item_url_base, json={"answer_index": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer_index"] == 2
    assert data["verifier_status"] is None
    assert data["verifier_answer_index"] is None
    assert data["verifier_note"] is None
    assert data["verified_at"] is None

    # 4. Approve → approved, verifier_status still None
    resp = await admin_client.post(f"{item_url_base}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["verifier_status"] is None
    assert data["approved_by"] is not None
    assert data["approved_at"] is not None
