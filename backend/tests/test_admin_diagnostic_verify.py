"""TDD tests for Task 3: sweep endpoint + verifier field exposure.

Step 1 (tests first, run to fail, then implement):

Coverage:
- unauth → 401/403 on the verify endpoint
- sweep verifies matching items, sets verifier fields, returns counts
- seed a known-wrong item → appears in flagged with verifier_status="mismatch"
- status="approved" filter only sweeps approved items
- only_unverified=true skips already-verified items
- limit bounds the sweep count
- invalid tier → 422
- list endpoint exposes verifier fields on each item
- verifier=needs_review filter returns only mismatch/ambiguous items
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.diagnostic import DiagnosticItem

pytestmark = pytest.mark.asyncio(loop_scope="session")

_MODULE = "app.services.diagnostic_item_service"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VERIFY_URL = "/admin/diagnostic-items/verify"
_LIST_URL = "/admin/diagnostic-items"


def _verifier_response(answer_index: int, ambiguous: bool = False, note: str = "ok") -> str:
    return json.dumps({"answer_index": answer_index, "ambiguous": ambiguous, "note": note})


def _batch_verifier_response(item_id, answer_index: int, ambiguous: bool = False, note: str = "ok") -> str:
    """A single-item batch verifier response — mocks the mini-batch LLM call shape."""
    return json.dumps(
        {"results": [{"id": str(item_id), "answer_index": answer_index, "ambiguous": ambiguous, "note": note}]}
    )


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
# Unauth — verify endpoint
# ---------------------------------------------------------------------------


async def test_verify_requires_auth(client):
    resp = await client.post(_VERIFY_URL, json={"limit": 5})
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Sweep: basic functionality
# ---------------------------------------------------------------------------


async def test_sweep_verifies_items_and_returns_counts(admin_client, db_session):
    """Sweep runs verify_item on matching items and returns the summary counts."""
    await _seed(db_session, status="approved", topic="budgeting", answer_index=2)

    mock_client = AsyncMock()
    # Verifier agrees with the declared answer
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=2))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        resp = await admin_client.post(
            _VERIFY_URL,
            json={"topic": "budgeting", "status": "approved", "limit": 10},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] >= 1
    assert "agree" in data
    assert "mismatch" in data
    assert "ambiguous" in data
    assert "error" in data
    assert "flagged" in data
    # Flagged is a list
    assert isinstance(data["flagged"], list)


async def test_sweep_mismatch_item_appears_in_flagged(admin_client, db_session):
    """An item where the verifier disagrees → appears in flagged with mismatch."""
    # Declared answer is index 0; verifier will pick index 3 → mismatch
    item = await _seed(
        db_session,
        status="approved",
        topic="mismatch_topic",
        market_code="GB",
        answer_index=0,
    )

    mock_client = AsyncMock()
    # Verifier picks a different answer → mismatch
    mock_client.complete = AsyncMock(return_value=_batch_verifier_response(item.id, answer_index=3))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        resp = await admin_client.post(
            _VERIFY_URL,
            json={
                "market_code": "GB",
                "topic": "mismatch_topic",
                "status": "approved",
                "limit": 10,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mismatch"] >= 1
    flagged_ids = [f["id"] for f in data["flagged"]]
    assert str(item.id) in flagged_ids

    # The flagged entry should have the expected shape
    flagged_entry = next(f for f in data["flagged"] if f["id"] == str(item.id))
    assert flagged_entry["verifier_status"] == "mismatch"
    assert flagged_entry["verifier_answer_index"] == 3
    assert "topic" in flagged_entry
    assert "difficulty_tier" in flagged_entry
    assert "answer_index" in flagged_entry
    assert "verifier_note" in flagged_entry


async def test_sweep_ambiguous_item_appears_in_flagged(admin_client, db_session):
    """An ambiguous item also appears in flagged."""
    item = await _seed(
        db_session,
        status="approved",
        topic="ambig_topic",
        market_code="US",
        answer_index=1,
    )

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(
        return_value=_batch_verifier_response(item.id, answer_index=1, ambiguous=True, note="two valid answers")
    )

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        resp = await admin_client.post(
            _VERIFY_URL,
            json={"market_code": "US", "topic": "ambig_topic", "limit": 10},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ambiguous"] >= 1
    flagged_ids = [f["id"] for f in data["flagged"]]
    assert str(item.id) in flagged_ids
    flagged_entry = next(f for f in data["flagged"] if f["id"] == str(item.id))
    assert flagged_entry["verifier_status"] == "ambiguous"


# ---------------------------------------------------------------------------
# Sweep: status filter
# ---------------------------------------------------------------------------


async def test_sweep_status_filter_only_touches_approved(admin_client, db_session):
    """Passing status='approved' sweeps only approved items, not drafts."""
    approved = await _seed(
        db_session,
        status="approved",
        topic="status_filter_topic",
        market_code="US",
        answer_index=0,
    )
    draft = await _seed(
        db_session,
        status="draft",
        topic="status_filter_topic",
        market_code="US",
        answer_index=0,
    )

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=0))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        resp = await admin_client.post(
            _VERIFY_URL,
            json={
                "market_code": "US",
                "topic": "status_filter_topic",
                "status": "approved",
                "limit": 10,
            },
        )

    assert resp.status_code == 200

    # Reload from DB
    await db_session.refresh(approved)
    await db_session.refresh(draft)

    assert approved.verifier_status is not None  # was swept
    assert draft.verifier_status is None  # was NOT swept (filtered out)


# ---------------------------------------------------------------------------
# Sweep: only_unverified filter
# ---------------------------------------------------------------------------


async def test_sweep_only_unverified_skips_already_verified(admin_client, db_session):
    """only_unverified=true skips items that already have a verifier_status."""
    already_verified = await _seed(
        db_session,
        status="approved",
        topic="unverified_topic",
        market_code="US",
        verifier_status="agree",
        verifier_answer_index=0,
        verified_at=datetime.now(UTC),
    )
    unverified = await _seed(
        db_session,
        status="approved",
        topic="unverified_topic",
        market_code="US",
    )

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=0))
    call_count = [0]

    async def count_calls(**kwargs):
        call_count[0] += 1
        return _verifier_response(answer_index=0)

    mock_client.complete = count_calls

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        resp = await admin_client.post(
            _VERIFY_URL,
            json={
                "market_code": "US",
                "topic": "unverified_topic",
                "only_unverified": True,
                "limit": 10,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    # Only the unverified item should have been swept
    assert data["verified"] >= 1
    # LLM should have been called exactly once (for the unverified item)
    assert call_count[0] == 1

    await db_session.refresh(already_verified)
    await db_session.refresh(unverified)
    # The already-verified item's status must NOT have changed
    assert already_verified.verifier_status == "agree"
    # The unverified item should now have a verifier status
    assert unverified.verifier_status is not None


# ---------------------------------------------------------------------------
# Sweep: limit
# ---------------------------------------------------------------------------


async def test_sweep_limit_bounds_count(admin_client, db_session):
    """limit=1 sweeps at most 1 item even if more match."""
    for _ in range(3):
        await _seed(
            db_session,
            status="approved",
            topic="limit_topic",
            market_code="US",
        )

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=0))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        resp = await admin_client.post(
            _VERIFY_URL,
            json={
                "market_code": "US",
                "topic": "limit_topic",
                "limit": 1,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] == 1


# ---------------------------------------------------------------------------
# Sweep: invalid tier → 422
# ---------------------------------------------------------------------------


async def test_sweep_invalid_tier_returns_422(admin_client, db_session):
    """Passing an invalid tier value must return 422."""
    resp = await admin_client.post(
        _VERIFY_URL,
        json={"limit": 5, "tier": "ultra"},
    )
    assert resp.status_code == 422


async def test_sweep_valid_tiers_accepted(admin_client, db_session):
    """lite, standard, premium are all valid tier values."""
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=0))

    for tier in ("lite", "standard", "premium"):
        with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
            resp = await admin_client.post(
                _VERIFY_URL,
                json={"limit": 0, "tier": tier},  # limit=0 → sweep nothing; just check 200
            )
        assert resp.status_code == 200, f"tier={tier!r} should be accepted but got {resp.status_code}"


# ---------------------------------------------------------------------------
# Sweep: best-effort (one error doesn't abort)
# ---------------------------------------------------------------------------


async def test_sweep_verifier_error_does_not_abort_sweep(admin_client, db_session):
    """If a mini-batch's verifier call throws, the sweep continues (other mini-batch
    sweeps unaffected) and reports the error count for that mini-batch's items.

    With batched verification, items sharing a mini-batch (<=8 items) share a
    single LLM call — so a call failure errors the whole mini-batch, not just one
    item. This is exercised across TWO separate sweep calls (two distinct topics,
    each with a single item, so each is its own mini-batch) to prove one
    mini-batch failing doesn't aborts the other sweep's outcome.
    """
    await _seed(
        db_session, status="approved", topic="best_effort_topic_a", market_code="US"
    )
    item_b = await _seed(
        db_session, status="approved", topic="best_effort_topic_b", market_code="US"
    )

    call_count = [0]

    async def flaky_complete(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("LLM exploded")
        return _batch_verifier_response(item_b.id, answer_index=0)

    mock_client = AsyncMock()
    mock_client.complete = flaky_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        resp_a = await admin_client.post(
            _VERIFY_URL,
            json={"market_code": "US", "topic": "best_effort_topic_a", "limit": 10},
        )
        resp_b = await admin_client.post(
            _VERIFY_URL,
            json={"market_code": "US", "topic": "best_effort_topic_b", "limit": 10},
        )

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    data_a = resp_a.json()
    data_b = resp_b.json()
    # Both items were processed (best-effort; one mini-batch errored, the other agreed)
    assert data_a["verified"] == 1
    assert data_b["verified"] == 1
    assert data_a["error"] == 1
    assert data_b["agree"] == 1


# ---------------------------------------------------------------------------
# List endpoint: verifier fields exposed
# ---------------------------------------------------------------------------


async def test_list_exposes_verifier_fields(admin_client, db_session):
    """GET /admin/diagnostic-items must include verifier_* fields in each item."""
    item = await _seed(
        db_session,
        status="approved",
        topic="verifier_fields_topic",
        verifier_status="agree",
        verifier_answer_index=0,
        verifier_note="Looks good",
        verified_at=datetime.now(UTC),
    )

    resp = await admin_client.get(_LIST_URL + "?topic=verifier_fields_topic")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1

    matched = next((i for i in items if i["id"] == str(item.id)), None)
    assert matched is not None, "seeded item not found in list response"

    assert matched["verifier_status"] == "agree"
    assert matched["verifier_answer_index"] == 0
    assert matched["verifier_note"] == "Looks good"
    assert matched["verified_at"] is not None


async def test_list_verifier_fields_null_for_unverified(admin_client, db_session):
    """Unverified items have null verifier_* fields in the list response."""
    item = await _seed(
        db_session,
        status="draft",
        topic="null_verifier_topic",
    )

    resp = await admin_client.get(_LIST_URL + "?topic=null_verifier_topic")
    assert resp.status_code == 200
    items = resp.json()["items"]
    matched = next((i for i in items if i["id"] == str(item.id)), None)
    assert matched is not None

    assert matched["verifier_status"] is None
    assert matched["verifier_answer_index"] is None
    assert matched["verifier_note"] is None
    assert matched["verified_at"] is None


# ---------------------------------------------------------------------------
# List endpoint: verifier=needs_review filter
# ---------------------------------------------------------------------------


async def test_list_verifier_needs_review_filter(admin_client, db_session):
    """verifier=needs_review returns only items with verifier_status in (mismatch, ambiguous)."""
    mismatch_item = await _seed(
        db_session,
        topic="needs_review_topic",
        verifier_status="mismatch",
        verifier_answer_index=2,
        verified_at=datetime.now(UTC),
    )
    ambiguous_item = await _seed(
        db_session,
        topic="needs_review_topic",
        verifier_status="ambiguous",
        verifier_answer_index=1,
        verified_at=datetime.now(UTC),
    )
    agree_item = await _seed(
        db_session,
        topic="needs_review_topic",
        verifier_status="agree",
        verifier_answer_index=0,
        verified_at=datetime.now(UTC),
    )
    unverified_item = await _seed(
        db_session,
        topic="needs_review_topic",
    )

    resp = await admin_client.get(
        _LIST_URL + "?topic=needs_review_topic&verifier=needs_review"
    )
    assert resp.status_code == 200
    returned_ids = {i["id"] for i in resp.json()["items"]}

    assert str(mismatch_item.id) in returned_ids
    assert str(ambiguous_item.id) in returned_ids
    assert str(agree_item.id) not in returned_ids
    assert str(unverified_item.id) not in returned_ids


async def test_list_verifier_filter_without_value_returns_all(admin_client, db_session):
    """When verifier param is absent (or unrecognised), all items are returned normally."""
    mismatch_item = await _seed(
        db_session,
        topic="no_verifier_filter_topic",
        verifier_status="mismatch",
        verified_at=datetime.now(UTC),
    )
    unverified_item = await _seed(
        db_session,
        topic="no_verifier_filter_topic",
    )

    resp = await admin_client.get(_LIST_URL + "?topic=no_verifier_filter_topic")
    assert resp.status_code == 200
    returned_ids = {i["id"] for i in resp.json()["items"]}

    assert str(mismatch_item.id) in returned_ids
    assert str(unverified_item.id) in returned_ids
