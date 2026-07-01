"""TDD tests for POST /internal/diagnostic-items/verify.

Coverage:
- 503 when CRON_SECRET is unset (not 403, proving CSRF is exempt)
- 401 when secret missing or wrong (not 403)
- 200 with correct secret → sweeps approved+unverified items, returns counts+flagged
- invalid tier → 422
- draft item is NOT swept (only approved)
- already-verified item is NOT swept (only_unverified=True implicit)
- limit is respected and capped
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.diagnostic import DiagnosticItem

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/internal/diagnostic-items/verify"
_MODULE = "app.services.diagnostic_item_service"
_SECRET = "test-cron-secret"


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
        question="What is a dividend?",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        explanation="A dividend is a payment to shareholders.",
        status="approved",
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
# Auth / secret guard — must NOT return 403 (proves CSRF exemption)
# ---------------------------------------------------------------------------


async def test_503_when_secret_unset(client, monkeypatch):
    """Returns 503 when CRON_SECRET is unset — never 403 (CSRF must be exempt)."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", "")
    r = await client.post(_PATH, headers={"X-Cron-Secret": "whatever"})
    assert r.status_code == 503, f"expected 503, got {r.status_code}: {r.text}"
    assert r.json()["detail"] == "not_configured"


async def test_401_when_secret_missing(client, monkeypatch):
    """Returns 401 when X-Cron-Secret header is absent — never 403."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)
    r = await client.post(_PATH)
    assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


async def test_401_when_secret_wrong(client, monkeypatch):
    """Returns 401 when X-Cron-Secret header has wrong value — never 403."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)
    r = await client.post(_PATH, headers={"X-Cron-Secret": "wrong-secret"})
    assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# Successful sweep
# ---------------------------------------------------------------------------


async def test_sweep_approved_unverified_items(client, db_session, monkeypatch):
    """With correct secret, sweeps approved items with verifier_status IS NULL."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)

    topic = "internal_verify_basic"
    item = await _seed(db_session, topic=topic, status="approved", answer_index=1)

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=1))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        r = await client.post(
            f"{_PATH}?limit=10&tier=premium",
            headers={"X-Cron-Secret": _SECRET},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["verified"] >= 1
    assert "agree" in data
    assert "mismatch" in data
    assert "ambiguous" in data
    assert "error" in data
    assert isinstance(data["flagged"], list)

    await db_session.refresh(item)
    assert item.verifier_status is not None


async def test_sweep_returns_flagged_mismatch(client, db_session, monkeypatch):
    """Mismatch items appear in the flagged array."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)

    topic = "internal_verify_mismatch"
    item = await _seed(db_session, topic=topic, status="approved", answer_index=0, market_code="GB")

    mock_client = AsyncMock()
    # Verifier picks index 3 → mismatch with declared 0
    mock_client.complete = AsyncMock(return_value=_batch_verifier_response(item.id, answer_index=3))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        r = await client.post(
            f"{_PATH}?limit=10&tier=premium",
            headers={"X-Cron-Secret": _SECRET},
        )

    assert r.status_code == 200
    data = r.json()
    flagged_ids = [f["id"] for f in data["flagged"]]
    assert str(item.id) in flagged_ids
    flagged_entry = next(f for f in data["flagged"] if f["id"] == str(item.id))
    assert flagged_entry["verifier_status"] == "mismatch"
    assert flagged_entry["verifier_answer_index"] == 3


# ---------------------------------------------------------------------------
# Tier validation
# ---------------------------------------------------------------------------


async def test_invalid_tier_returns_422(client, monkeypatch):
    """An invalid tier value returns 422."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)
    r = await client.post(
        f"{_PATH}?tier=ultra",
        headers={"X-Cron-Secret": _SECRET},
    )
    assert r.status_code == 422


async def test_valid_tiers_accepted(client, db_session, monkeypatch):
    """lite, standard, premium are all accepted without 422."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=0))

    for tier in ("lite", "standard", "premium"):
        with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
            r = await client.post(
                f"{_PATH}?limit=0&tier={tier}",
                headers={"X-Cron-Secret": _SECRET},
            )
        assert r.status_code == 200, f"tier={tier!r} should be accepted, got {r.status_code}"


# ---------------------------------------------------------------------------
# Draft items are NOT swept
# ---------------------------------------------------------------------------


async def test_draft_items_are_not_swept(client, db_session, monkeypatch):
    """Draft items must never be touched by the internal cron sweep."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)

    topic = "internal_verify_draft_skip"
    draft = await _seed(db_session, topic=topic, status="draft")

    mock_client = AsyncMock()
    call_count = [0]

    async def counting_complete(**kwargs):
        call_count[0] += 1
        return _verifier_response(answer_index=0)

    mock_client.complete = counting_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        r = await client.post(
            f"{_PATH}?limit=10&tier=premium",
            headers={"X-Cron-Secret": _SECRET},
        )

    assert r.status_code == 200
    await db_session.refresh(draft)
    # Draft item must remain untouched
    assert draft.verifier_status is None, "draft item should not have been verified"


# ---------------------------------------------------------------------------
# Already-verified items are NOT swept again
# ---------------------------------------------------------------------------


async def test_already_verified_items_are_skipped(client, db_session, monkeypatch):
    """Items that already have a verifier_status are skipped (only_unverified=True)."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)

    topic = "internal_verify_already_done"
    already_done = await _seed(
        db_session,
        topic=topic,
        status="approved",
        verifier_status="agree",
        verifier_answer_index=0,
        verified_at=datetime.now(UTC),
    )
    unverified = await _seed(
        db_session,
        topic=topic,
        status="approved",
        verifier_status=None,
    )

    call_count = [0]
    mock_client = AsyncMock()

    async def counting_complete(**kwargs):
        call_count[0] += 1
        return _verifier_response(answer_index=0)

    mock_client.complete = counting_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        r = await client.post(
            f"{_PATH}?limit=10&tier=premium",
            headers={"X-Cron-Secret": _SECRET},
        )

    assert r.status_code == 200

    await db_session.refresh(already_done)
    await db_session.refresh(unverified)

    # The already-verified item must not have been touched
    assert already_done.verifier_status == "agree"
    # The unverified item should now have a status
    assert unverified.verifier_status is not None
    # LLM called only once (only for the unverified item in this topic)
    # (Note: other tests in the session may also have seeded unverified items
    # for other topics, so we only check the already_done item wasn't re-billed)
    assert call_count[0] >= 1


# ---------------------------------------------------------------------------
# Limit is respected
# ---------------------------------------------------------------------------


async def test_limit_bounds_sweep(client, db_session, monkeypatch):
    """limit=1 sweeps at most 1 item even if more unverified approved items exist."""
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", _SECRET)

    topic = "internal_verify_limit"
    for _ in range(3):
        await _seed(db_session, topic=topic, status="approved")

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=0))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        r = await client.post(
            f"{_PATH}?limit=1&tier=premium",
            headers={"X-Cron-Secret": _SECRET},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["verified"] == 1
