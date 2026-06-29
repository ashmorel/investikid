"""TDD: diagnostic item generation service.

Covers:
  (a) A valid generated MCQ persists with status="draft", source="generated",
      and the requested market/topic/difficulty_tier.
  (b) A moderation-failing item is dropped (not persisted).
  (c) Malformed items are dropped — too few choices, answer_index out of range,
      or empty question / explanation.
  (d) count requested items → that many draft rows when all valid.
  (e) A concept_slug the LLM emits that resolves in the taxonomy sets concept_id;
      an unresolvable slug yields concept_id=NULL but the item still persists.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.concept import Concept
from app.models.diagnostic import DiagnosticItem
from app.services.diagnostic_item_service import generate_items
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mcq(
    question: str = "What is a stock?",
    choices: list[str] | None = None,
    answer_index: int = 0,
    explanation: str = "A stock is a share of ownership.",
    concept_slug: str | None = None,
) -> dict:
    item: dict = {
        "question": question,
        "choices": choices if choices is not None else ["A share", "A bond", "A loan", "Cash"],
        "answer_index": answer_index,
        "explanation": explanation,
    }
    if concept_slug is not None:
        item["concept_slug"] = concept_slug
    return item


def _llm_response(items: list[dict]) -> str:
    """Wrap items in the object envelope that response_format='json' produces."""
    return json.dumps({"items": items})


_SAFE = ModerationResult(safe=True, category=None, text="x")
_UNSAFE = ModerationResult(safe=False, category="violence", text="x")

_MODULE = "app.services.diagnostic_item_service"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_valid_item_persisted_as_draft(db_session):
    """A clean MCQ from the LLM is persisted with the correct metadata."""
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_llm_response([_mcq()]))

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
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
    assert item.status == "draft"
    assert item.source == "generated"
    assert item.market_code == "GB"
    assert item.topic == "stocks"
    assert item.difficulty_tier == 1
    assert item.answer_index == 0
    assert len(item.choices) == 4


async def test_moderation_failing_item_dropped(db_session):
    """An item that fails moderation is NOT persisted."""
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_llm_response([_mcq()]))

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
        patch(f"{_MODULE}.moderate_output", AsyncMock(return_value=_UNSAFE)),
    ):
        results = await generate_items(
            db_session,
            market_code="US",
            topic="savings",
            difficulty_tier=2,
            count=1,
        )

    assert results == []
    rows = (await db_session.scalars(
        select(DiagnosticItem).where(
            DiagnosticItem.topic == "savings",
            DiagnosticItem.market_code == "US",
        )
    )).all()
    assert len(rows) == 0


async def test_malformed_three_choices_dropped(db_session):
    """Items with fewer than 4 choices are dropped without persisting."""
    bad = _mcq(choices=["A", "B", "C"])  # only 3 choices
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_llm_response([bad]))

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
        patch(f"{_MODULE}.moderate_output", AsyncMock(return_value=_SAFE)) as mock_mod,
    ):
        results = await generate_items(
            db_session,
            market_code="GB",
            topic="budgeting",
            difficulty_tier=1,
            count=1,
        )

    assert results == []
    # Moderation should NOT be called on a structurally invalid item.
    mock_mod.assert_not_called()


async def test_malformed_answer_index_out_of_range_dropped(db_session):
    """Items with answer_index >= 4 are dropped."""
    bad = _mcq(answer_index=9)
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_llm_response([bad]))

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
        patch(f"{_MODULE}.moderate_output", AsyncMock(return_value=_SAFE)) as mock_mod,
    ):
        results = await generate_items(
            db_session,
            market_code="GB",
            topic="risk",
            difficulty_tier=2,
            count=1,
        )

    assert results == []
    mock_mod.assert_not_called()


async def test_malformed_empty_question_dropped(db_session):
    """Items with an empty question are dropped."""
    bad = _mcq(question="")
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_llm_response([bad]))

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
        patch(f"{_MODULE}.moderate_output", AsyncMock(return_value=_SAFE)) as mock_mod,
    ):
        results = await generate_items(
            db_session,
            market_code="GB",
            topic="debt",
            difficulty_tier=3,
            count=1,
        )

    assert results == []
    mock_mod.assert_not_called()


async def test_count_items_all_valid(db_session):
    """When all N items are valid and safe, N drafts are persisted."""
    items = [_mcq(question=f"Question {i}?") for i in range(3)]
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_llm_response(items))

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
        patch(f"{_MODULE}.moderate_output", AsyncMock(return_value=_SAFE)),
    ):
        results = await generate_items(
            db_session,
            market_code="CA",
            topic="taxes",
            difficulty_tier=2,
            count=3,
        )

    assert len(results) == 3
    assert all(r.status == "draft" for r in results)
    assert all(r.source == "generated" for r in results)
    assert all(r.market_code == "CA" for r in results)
    assert all(r.topic == "taxes" for r in results)
    assert all(r.difficulty_tier == 2 for r in results)


async def test_concept_slug_resolves_to_concept_id(db_session):
    """When the LLM emits a resolvable concept_slug, concept_id is set."""
    concept = Concept(
        topic="stocks",
        slug="common-stock",
        name="Common Stock",
        blurb="A type of equity.",
        difficulty_tier=1,
        order_index=0,
    )
    db_session.add(concept)
    await db_session.flush()

    item = _mcq(concept_slug="common-stock")
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_llm_response([item]))

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
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
    assert results[0].concept_id == concept.id


async def test_unresolvable_concept_slug_yields_null(db_session):
    """An unresolvable concept_slug does NOT block persistence; concept_id is NULL."""
    item = _mcq(concept_slug="totally-unknown-slug-xyz-123")
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_llm_response([item]))

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
        patch(f"{_MODULE}.moderate_output", AsyncMock(return_value=_SAFE)),
    ):
        results = await generate_items(
            db_session,
            market_code="GB",
            topic="crypto",
            difficulty_tier=3,
            count=1,
        )

    assert len(results) == 1
    assert results[0].concept_id is None


async def test_mixed_valid_invalid_persists_only_valid(db_session):
    """Valid and invalid items in the same batch: only valid ones are persisted."""
    good = _mcq(question="What is diversification?")
    bad_few_choices = _mcq(question="Bad item?", choices=["A", "B"])

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(
        return_value=_llm_response([good, bad_few_choices])
    )

    call_count = 0

    async def mock_moderate(text, *, surface, language="en"):
        nonlocal call_count
        call_count += 1
        return _SAFE

    with (
        patch(f"{_MODULE}.get_llm_client", return_value=mock_client),
        patch(f"{_MODULE}.moderate_output", side_effect=mock_moderate),
    ):
        results = await generate_items(
            db_session,
            market_code="GB",
            topic="entrepreneurship",
            difficulty_tier=2,
            count=2,
        )

    assert len(results) == 1
    assert results[0].question == "What is diversification?"
    # Moderation called only once (for the structurally valid item)
    assert call_count == 1
