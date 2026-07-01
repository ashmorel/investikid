"""TDD: batched verification for run_verify_sweep.

Covers:
  1. Verifying N items makes ceil(N/8) LLM calls, not N.
  2. A mini-batch response missing one item's id marks JUST that item
     verifier_status="error"; batch-mates unaffected.
  3. A mini-batch whose LLM call raises marks only that mini-batch's items
     as verifier_status="error".
  4. Bracket-echo tolerance ("[1]" / [1]) still works inside a batched response.
  5. run_verify_sweep's flagged list / counts are correct across a mix of
     agree/mismatch/ambiguous/error spanning multiple mini-batches.
"""
from __future__ import annotations

import json
import math
from unittest.mock import AsyncMock, patch

import pytest

from app.models.diagnostic import DiagnosticItem
from app.services.diagnostic_item_service import run_verify_sweep

pytestmark = pytest.mark.asyncio(loop_scope="session")

_MODULE = "app.services.diagnostic_item_service"
_BATCH_SIZE = 8


async def _seed(db_session, **kwargs) -> DiagnosticItem:
    defaults = dict(
        market_code="US",
        topic="batch_topic",
        difficulty_tier=1,
        question="What is a share?",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        explanation="A share is part of a company.",
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


def _batch_response(results: list[dict]) -> str:
    return json.dumps({"results": results})


# ---------------------------------------------------------------------------
# 1. Call count: ceil(N/8) LLM calls, not N.
# ---------------------------------------------------------------------------


async def test_sweep_batches_calls_ceil_n_over_8(db_session):
    n = 19
    topic = "batch_call_count"
    items = [await _seed(db_session, topic=topic, answer_index=0) for _ in range(n)]

    call_count = [0]

    async def fake_complete(**kwargs):
        call_count[0] += 1
        # Figure out which ids were asked about via the prompt content isn't needed;
        # just agree with every item's declared answer_index=0.
        # Extract ids from the user message content (batch prompt lists them).
        content = kwargs["system_prompt"]
        ids_in_batch = [str(it.id) for it in items if str(it.id) in content]
        return _batch_response(
            [{"id": i, "answer_index": 0, "ambiguous": False, "note": "ok"} for i in ids_in_batch]
        )

    mock_client = AsyncMock()
    mock_client.complete = fake_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        result = await run_verify_sweep(
            db_session,
            status="approved",
            market_code="US",
            topic=topic,
            limit=n,
            only_unverified=True,
            tier="premium",
        )

    assert call_count[0] == math.ceil(n / _BATCH_SIZE)
    assert result["verified"] == n
    assert result["agree"] == n


# ---------------------------------------------------------------------------
# 2. Missing id in batch response → only that item errors.
# ---------------------------------------------------------------------------


async def test_batch_missing_id_only_errors_that_item(db_session):
    topic = "batch_missing_id"
    items = [await _seed(db_session, topic=topic, answer_index=0) for _ in range(3)]

    async def fake_complete(**kwargs):
        # Omit the second item's id entirely from the response.
        results = [
            {"id": str(items[0].id), "answer_index": 0, "ambiguous": False, "note": "ok"},
            # items[1] deliberately missing
            {"id": str(items[2].id), "answer_index": 0, "ambiguous": False, "note": "ok"},
        ]
        return _batch_response(results)

    mock_client = AsyncMock()
    mock_client.complete = fake_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        result = await run_verify_sweep(
            db_session,
            status="approved",
            market_code="US",
            topic=topic,
            limit=10,
            only_unverified=True,
            tier="premium",
        )

    assert items[0].verifier_status == "agree"
    assert items[1].verifier_status == "error"
    assert items[2].verifier_status == "agree"
    assert result["error"] == 1
    assert result["agree"] == 2


async def test_batch_malformed_id_only_errors_that_item(db_session):
    """A malformed id (not matching any item) leaves that item unresolved (error);
    other batch-mates with valid ids are unaffected."""
    topic = "batch_malformed_id"
    items = [await _seed(db_session, topic=topic, answer_index=0) for _ in range(2)]

    async def fake_complete(**kwargs):
        results = [
            {"id": "not-a-real-uuid", "answer_index": 0, "ambiguous": False, "note": "ok"},
            {"id": str(items[0].id), "answer_index": 0, "ambiguous": False, "note": "ok"},
            {"id": str(items[1].id), "answer_index": 2, "ambiguous": False, "note": "ok"},
        ]
        return _batch_response(results)

    mock_client = AsyncMock()
    mock_client.complete = fake_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        result = await run_verify_sweep(
            db_session,
            status="approved",
            market_code="US",
            topic=topic,
            limit=10,
            only_unverified=True,
            tier="premium",
        )

    assert items[0].verifier_status == "agree"
    assert items[1].verifier_status == "mismatch"
    assert result["agree"] == 1
    assert result["mismatch"] == 1
    assert result["error"] == 0  # the bogus id has no corresponding item to mark


# ---------------------------------------------------------------------------
# 3. Whole mini-batch call raises → all items in that mini-batch error.
# ---------------------------------------------------------------------------


async def test_batch_call_raises_all_items_in_batch_error(db_session):
    topic = "batch_raises"
    items = [await _seed(db_session, topic=topic, answer_index=0) for _ in range(5)]

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=RuntimeError("provider rate limited"))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        result = await run_verify_sweep(
            db_session,
            status="approved",
            market_code="US",
            topic=topic,
            limit=10,
            only_unverified=True,
            tier="premium",
        )

    for item in items:
        assert item.verifier_status == "error"
        assert item.verifier_answer_index is None
        assert item.verifier_note is not None

    assert result["error"] == 5
    assert result["verified"] == 5


async def test_two_batches_one_raises_other_succeeds(db_session):
    """With >8 items (2 mini-batches), only the failing batch's items error."""
    topic = "batch_partial_failure"
    items = [await _seed(db_session, topic=topic, answer_index=0) for _ in range(10)]

    call_count = [0]

    async def fake_complete(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("boom on first batch")
        content = kwargs["system_prompt"]
        ids_in_batch = [str(it.id) for it in items if str(it.id) in content]
        return _batch_response(
            [{"id": i, "answer_index": 0, "ambiguous": False, "note": "ok"} for i in ids_in_batch]
        )

    mock_client = AsyncMock()
    mock_client.complete = fake_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        result = await run_verify_sweep(
            db_session,
            status="approved",
            market_code="US",
            topic=topic,
            limit=10,
            only_unverified=True,
            tier="premium",
        )

    assert call_count[0] == 2
    assert result["verified"] == 10
    assert result["error"] == 8  # first mini-batch (8 items) failed
    assert result["agree"] == 2  # second mini-batch (2 items) succeeded


# ---------------------------------------------------------------------------
# 4. Bracket-echo tolerance inside a batched response.
# ---------------------------------------------------------------------------


async def test_batch_bracket_echo_tolerance(db_session):
    topic = "batch_bracket_echo"
    item_bracket_str = await _seed(db_session, topic=topic, answer_index=1)
    item_bracket_list = await _seed(db_session, topic=topic, answer_index=2)

    async def fake_complete(**kwargs):
        results = [
            {"id": str(item_bracket_str.id), "answer_index": "[1]", "ambiguous": False, "note": "ok"},
            {"id": str(item_bracket_list.id), "answer_index": [2], "ambiguous": False, "note": "ok"},
        ]
        return _batch_response(results)

    mock_client = AsyncMock()
    mock_client.complete = fake_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        result = await run_verify_sweep(
            db_session,
            status="approved",
            market_code="US",
            topic=topic,
            limit=10,
            only_unverified=True,
            tier="premium",
        )

    assert item_bracket_str.verifier_status == "agree"
    assert item_bracket_str.verifier_answer_index == 1
    assert item_bracket_list.verifier_status == "agree"
    assert item_bracket_list.verifier_answer_index == 2
    assert result["agree"] == 2


# ---------------------------------------------------------------------------
# 5. Mixed outcomes across multiple mini-batches: counts + flagged correctness.
# ---------------------------------------------------------------------------


async def test_sweep_mixed_outcomes_across_multiple_batches(db_session):
    """17 items (3 mini-batches of 8/8/1) with a mix of agree/mismatch/ambiguous/error."""
    topic = "batch_mixed_outcomes"
    items = [await _seed(db_session, topic=topic, answer_index=0) for _ in range(17)]

    call_count = [0]

    async def fake_complete(**kwargs):
        call_count[0] += 1
        content = kwargs["system_prompt"]
        batch_items = [it for it in items if str(it.id) in content]

        if call_count[0] == 2:
            # Second mini-batch: whole call raises → all its items error.
            raise RuntimeError("second batch exploded")

        results = []
        for idx, it in enumerate(batch_items):
            if call_count[0] == 1 and idx == 0:
                results.append({"id": str(it.id), "answer_index": 3, "ambiguous": False, "note": "mismatch"})
            elif call_count[0] == 1 and idx == 1:
                results.append({"id": str(it.id), "answer_index": 0, "ambiguous": True, "note": "ambiguous"})
            else:
                results.append({"id": str(it.id), "answer_index": 0, "ambiguous": False, "note": "ok"})
        return _batch_response(results)

    mock_client = AsyncMock()
    mock_client.complete = fake_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        result = await run_verify_sweep(
            db_session,
            status="approved",
            market_code="US",
            topic=topic,
            limit=17,
            only_unverified=True,
            tier="premium",
        )

    assert call_count[0] == 3  # ceil(17/8) = 3
    assert result["verified"] == 17
    # First batch (8 items): 1 mismatch, 1 ambiguous, 6 agree
    # Second batch (8 items): all error (call raised)
    # Third batch (1 item): agree
    assert result["mismatch"] == 1
    assert result["ambiguous"] == 1
    assert result["error"] == 8
    assert result["agree"] == 7  # 6 from batch 1 + 1 from batch 3

    flagged_statuses = {f["verifier_status"] for f in result["flagged"]}
    assert flagged_statuses == {"mismatch", "ambiguous"}
    assert len(result["flagged"]) == 2
    # Errors must NOT appear in flagged (matches existing single-item semantics)
    for f in result["flagged"]:
        assert f["verifier_status"] != "error"
