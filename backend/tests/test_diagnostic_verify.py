"""TDD: independent answer verifier for diagnostic items.

Covers:
  (a) Verifier agrees with declared answer (not ambiguous) → verifier_status="agree".
  (b) Verifier picks a different index → verifier_status="mismatch", verifier_answer_index stored.
  (c) Verifier flags ambiguity → verifier_status="ambiguous".
  (d) LLM raises an exception → verifier_status="error", no exception propagates.
  (e) Blindness: the prompt passed to the LLM does NOT contain the declared answer index or
      any labelling of the correct choice — the verifier must be unable to simply copy the
      declared answer from its own prompt.
  (f) generate_items sets a verifier_status on each persisted draft.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.diagnostic import DiagnosticItem
from app.services.diagnostic_item_service import generate_items, verify_item
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

_MODULE = "app.services.diagnostic_item_service"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAFE = ModerationResult(safe=True, category=None, text="x")


def _make_item(
    *,
    question: str = "A shop sells pencils for 10p each. If it costs 5p to make one, what is the break-even quantity?",
    choices: list[str] | None = None,
    answer_index: int = 1,
) -> DiagnosticItem:
    """Build an in-memory DiagnosticItem (not flushed to DB) for verifier tests."""
    return DiagnosticItem(
        market_code="GB",
        topic="budgeting",
        difficulty_tier=2,
        question=question,
        choices=choices or [
            "5 pencils",
            "10 pencils",
            "20 pencils",
            "50 pencils",
        ],
        answer_index=answer_index,
        explanation="Break-even means revenue equals cost.",
        status="draft",
        source="generated",
    )


def _verifier_response(
    answer_index: int,
    ambiguous: bool = False,
    note: str = "Clear answer.",
) -> str:
    """Wrap in the object envelope (response_format=json forces an object wrapper)."""
    return json.dumps({
        "answer_index": answer_index,
        "ambiguous": ambiguous,
        "note": note,
    })


# ---------------------------------------------------------------------------
# Tests: verify_item status outcomes
# ---------------------------------------------------------------------------


async def test_verifier_agree(db_session):
    """Verifier picks the same index, not ambiguous → status='agree'."""
    item = _make_item(answer_index=1)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=1, ambiguous=False))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        await verify_item(db_session, item, tier="premium")

    assert item.verifier_status == "agree"
    assert item.verifier_answer_index == 1
    assert item.verifier_note is not None
    assert item.verified_at is not None


async def test_verifier_mismatch(db_session):
    """Verifier picks a different index → status='mismatch', verifier_answer_index stored."""
    item = _make_item(answer_index=1)
    mock_client = AsyncMock()
    # verifier thinks answer is index 2, not 1
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=2, ambiguous=False))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        await verify_item(db_session, item, tier="premium")

    assert item.verifier_status == "mismatch"
    assert item.verifier_answer_index == 2
    assert item.answer_index == 1  # declared answer MUST NOT be changed
    assert item.verified_at is not None


async def test_verifier_ambiguous(db_session):
    """Verifier flags ambiguous=True → status='ambiguous', regardless of index match."""
    item = _make_item(answer_index=1)
    mock_client = AsyncMock()
    # Even though index matches, ambiguous flag wins
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=1, ambiguous=True))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        await verify_item(db_session, item, tier="premium")

    assert item.verifier_status == "ambiguous"
    assert item.verified_at is not None


async def test_verifier_ambiguous_different_index(db_session):
    """Verifier flags ambiguous=True with a different index → still 'ambiguous'."""
    item = _make_item(answer_index=1)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_verifier_response(answer_index=3, ambiguous=True))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        await verify_item(db_session, item, tier="premium")

    assert item.verifier_status == "ambiguous"
    assert item.verifier_answer_index == 3


async def test_verifier_llm_error(db_session):
    """LLM raises → verifier_status='error', no exception propagates."""
    item = _make_item(answer_index=0)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=RuntimeError("API timeout"))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        await verify_item(db_session, item, tier="premium")  # must NOT raise

    assert item.verifier_status == "error"
    assert item.verifier_answer_index is None
    assert item.verifier_note is not None  # error message stored
    assert item.verified_at is not None


async def test_verifier_garbage_response(db_session):
    """LLM returns unparseable garbage → verifier_status='error', no crash."""
    item = _make_item(answer_index=0)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="not json at all !!!!")

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        await verify_item(db_session, item, tier="premium")

    assert item.verifier_status == "error"
    assert item.verifier_answer_index is None


async def test_verifier_missing_answer_index_field(db_session):
    """LLM returns JSON missing the answer_index field → verifier_status='error'."""
    item = _make_item(answer_index=0)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=json.dumps({"note": "hmm", "ambiguous": False}))

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        await verify_item(db_session, item, tier="premium")

    assert item.verifier_status == "error"


# ---------------------------------------------------------------------------
# Test: blindness — the declared answer must NOT appear in the prompt
# ---------------------------------------------------------------------------


async def test_verifier_prompt_is_blind(db_session):
    """The verifier prompt must NOT include the declared answer value or label any choice correct.

    Blindness means the prompt:
    1. Contains the question and ALL choices (model must see the options).
    2. Does NOT reveal which choice is declared correct — no "correct answer is X",
       no "the answer is index N", no "declared_answer: N", no "answer_index: 1"
       (the VALUE, not the JSON key name used in the response spec).
    3. Does NOT label the correct choice text as "correct".

    We capture the call kwargs and inspect the full text sent to the model.
    """
    item = _make_item(answer_index=1)  # declared correct is index 1 = "10 pencils"
    mock_client = AsyncMock()

    captured_calls: list[dict] = []

    async def capture_complete(**kwargs):
        captured_calls.append(kwargs)
        return _verifier_response(answer_index=1)

    mock_client.complete = capture_complete

    with patch(f"{_MODULE}.get_llm_client", return_value=mock_client):
        await verify_item(db_session, item, tier="premium")

    assert len(captured_calls) == 1
    call = captured_calls[0]

    # Reconstruct the full text fed to the LLM
    system_prompt: str = call.get("system_prompt", "")
    messages: list = call.get("messages", [])
    all_text = system_prompt + " ".join(
        m.get("content", "") for m in messages if isinstance(m, dict)
    )

    lower = all_text.lower()

    # The question and all choices must be present (model needs them to solve it)
    assert item.question in all_text, "Question must be in the verifier prompt"
    assert "10 pencils" in all_text, "All choices must be in the verifier prompt"
    assert "5 pencils" in all_text, "All choices must be in the verifier prompt"

    # The declared CORRECT answer must NOT be revealed.
    # "answer_index: 1" or "answer_index=1" (value disclosure, not the JSON key name)
    assert "answer_index: 1" not in lower, (
        "Prompt must not reveal declared answer_index value"
    )
    assert "answer_index=1" not in lower
    # Must not say "correct answer is 1" or "correct index is 1"
    assert "correct answer is 1" not in lower
    assert "correct index is 1" not in lower
    assert "declared answer" not in lower, (
        "Prompt must not reference a 'declared answer'"
    )
    # The correct choice text must not be labelled as correct
    assert "correct: 10 pencils" not in lower
    assert "correct answer: 10 pencils" not in lower

    # The explanation must NOT be in the prompt (it hints at the answer)
    assert item.explanation not in all_text, (
        "The explanation must not be included in the blind verifier prompt"
    )


# ---------------------------------------------------------------------------
# Test: generate_items wires in verify_item
# ---------------------------------------------------------------------------


def _mcq(
    question: str = "What is a stock?",
    choices: list[str] | None = None,
    answer_index: int = 0,
    explanation: str = "A stock is a share of ownership.",
) -> dict:
    return {
        "question": question,
        "choices": choices or ["A share", "A bond", "A loan", "Cash"],
        "answer_index": answer_index,
        "explanation": explanation,
    }


def _llm_response(items: list[dict]) -> str:
    return json.dumps({"items": items})


async def test_generate_items_sets_verifier_status(db_session):
    """generate_items calls verify_item for each draft; each gets a verifier_status."""
    gen_client = AsyncMock()
    gen_client.complete = AsyncMock(return_value=_llm_response([_mcq(question="Q gen verify?")]))

    verify_client = AsyncMock()
    verify_client.complete = AsyncMock(
        return_value=_verifier_response(answer_index=0, ambiguous=False)
    )

    call_count = [0]

    def mock_get_llm_client(tier="lite"):
        call_count[0] += 1
        # First call is generation (standard tier), second is verification (premium tier)
        if tier == "premium":
            return verify_client
        return gen_client

    with (
        patch(f"{_MODULE}.get_llm_client", side_effect=mock_get_llm_client),
        patch(f"{_MODULE}.moderate_output", AsyncMock(return_value=_SAFE)),
    ):
        results = await generate_items(
            db_session,
            market_code="GB",
            topic="stocks",
            difficulty_tier=1,
            count=1,
        )

    assert len(results) == 1
    item = results[0]
    # Verifier must have run
    assert item.verifier_status is not None
    assert item.verifier_status in {"agree", "mismatch", "ambiguous", "error"}
    assert item.verified_at is not None


async def test_generate_items_verifier_error_does_not_abort(db_session):
    """A verifier LLM failure → verifier_status='error'; draft still persists."""
    gen_client = AsyncMock()
    gen_client.complete = AsyncMock(return_value=_llm_response([_mcq(question="Q verifier err?")]))

    verify_client = AsyncMock()
    verify_client.complete = AsyncMock(side_effect=RuntimeError("verifier boom"))

    def mock_get_llm_client(tier="lite"):
        if tier == "premium":
            return verify_client
        return gen_client

    with (
        patch(f"{_MODULE}.get_llm_client", side_effect=mock_get_llm_client),
        patch(f"{_MODULE}.moderate_output", AsyncMock(return_value=_SAFE)),
    ):
        results = await generate_items(
            db_session,
            market_code="GB",
            topic="risk",
            difficulty_tier=2,
            count=1,
        )

    assert len(results) == 1
    item = results[0]
    assert item.verifier_status == "error"
    assert item.status == "draft"  # item still persisted normally
