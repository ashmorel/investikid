"""Tests for arcade_word_admin_service (suggest_words) and arcade_words seed."""
import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.models.arcade_word import ArcadeWord
from app.seed.arcade_words import seed_arcade_words
from app.services.arcade_word_admin_service import suggest_words
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_WORD = "WALLET"         # exactly 6 letters, new, not a seed word
_WRONG_LENGTH = "INTEREST"     # a REAL word but 8 letters — must be skipped (length lock)
_DUPLICATE = "BUDGET"          # exactly 6 letters AND a seed word — skipped as a duplicate

_LLM_RESPONSE = json.dumps(
    [
        {"word": _VALID_WORD, "definition": "A small folded holder you keep your cash and cards in."},
        {"word": _WRONG_LENGTH, "definition": "Extra money a bank pays you for saving, or charges you for borrowing."},
        {"word": _DUPLICATE, "definition": "A plan for how much money you will spend and save."},
    ]
)


def _mock_llm_client(response: str = _LLM_RESPONSE) -> object:
    mock = AsyncMock()
    mock.complete = AsyncMock(return_value=response)
    return mock


# ---------------------------------------------------------------------------
# seed_arcade_words
# ---------------------------------------------------------------------------


async def test_seed_inserts_approved_words(db_session):
    count = await seed_arcade_words(db_session)
    assert count > 0
    total = await db_session.scalar(
        select(func.count()).select_from(ArcadeWord).where(ArcadeWord.language == "en")
    )
    assert total >= count


async def test_seed_idempotent(db_session):
    """Calling seed twice must not raise or insert duplicates."""
    first = await seed_arcade_words(db_session)
    second = await seed_arcade_words(db_session)
    assert second == 0  # second run inserts nothing new
    total = await db_session.scalar(
        select(func.count()).select_from(ArcadeWord).where(ArcadeWord.language == "en")
    )
    # total must not have doubled
    assert total == first


async def test_seed_words_are_approved(db_session):
    await seed_arcade_words(db_session)
    words = (
        await db_session.scalars(
            select(ArcadeWord).where(ArcadeWord.language == "en")
        )
    ).all()
    for w in words:
        assert w.status == "approved"
        assert w.source == "manual"


# ---------------------------------------------------------------------------
# suggest_words
# ---------------------------------------------------------------------------


async def test_suggest_words_inserts_valid_only(db_session):
    """Only the valid, new word is inserted as pending; long/dup are skipped."""
    # Ensure the duplicate seed word exists
    await seed_arcade_words(db_session)

    mock_client = _mock_llm_client()
    with patch(
        "app.services.arcade_word_admin_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await suggest_words(db_session, language="en")

    assert result["created"] == 1
    assert result["skipped"] == 2  # wrong-length (real but 8 letters) + duplicate

    row = await db_session.scalar(
        select(ArcadeWord).where(
            ArcadeWord.word == _VALID_WORD, ArcadeWord.language == "en"
        )
    )
    assert row is not None
    assert row.status == "pending"
    assert row.source == "llm"


async def test_suggest_words_skips_flagged_definition(db_session):
    """A definition that fails moderation is skipped even if the word is valid."""
    safe_response = json.dumps(
        [{"word": "POCKET", "definition": "How much an investment pays you back each year."}]
    )
    mock_client = _mock_llm_client(safe_response)

    unsafe_mod = ModerationResult(safe=False, category="test_flag", text="flagged")
    with (
        patch(
            "app.services.arcade_word_admin_service.get_llm_client",
            return_value=mock_client,
        ),
        patch(
            "app.services.arcade_word_admin_service.moderate_output",
            new=AsyncMock(return_value=unsafe_mod),
        ),
    ):
        result = await suggest_words(db_session, language="en")

    assert result["created"] == 0
    assert result["skipped"] == 1

    row = await db_session.scalar(
        select(ArcadeWord).where(ArcadeWord.word == "POCKET", ArcadeWord.language == "en")
    )
    assert row is None


async def test_suggest_words_skips_word_in_definition(db_session):
    """Word embedded in its own definition is rejected (answer leak)."""
    leak_response = json.dumps(
        [{"word": "MARKET", "definition": "A MARKET is where things are bought and sold."}]
    )
    mock_client = _mock_llm_client(leak_response)
    with patch(
        "app.services.arcade_word_admin_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await suggest_words(db_session, language="en")

    assert result["created"] == 0
    assert result["skipped"] == 1


async def test_suggest_words_skips_real_words_that_are_not_six_letters(db_session):
    """The length lock rejects REAL finance words that aren't exactly 6 letters,
    rather than letting the model truncate/pad them to fit (the reported bug)."""
    response = json.dumps(
        [
            {"word": "CASH", "definition": "Notes and coins you can spend straight away."},
            {"word": "INTEREST", "definition": "Extra money a bank adds to your savings over time."},
            {"word": "SAVING", "definition": "Money you keep instead of spending it right now."},
        ]
    )
    mock_client = _mock_llm_client(response)
    with patch(
        "app.services.arcade_word_admin_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await suggest_words(db_session, language="en")

    # Only SAVING (6 letters) survives; CASH (4) and INTEREST (8) are skipped.
    assert result["created"] == 1
    assert result["skipped"] == 2
    survivor = await db_session.scalar(
        select(ArcadeWord).where(ArcadeWord.word == "SAVING", ArcadeWord.language == "en")
    )
    assert survivor is not None and survivor.length == 6


async def test_suggest_words_sends_existing_words_as_avoid_list(db_session):
    """Existing bank words are passed to the LLM as a do-not-repeat list, so the
    suggester stops returning words we already have (the '0 queued' bug)."""
    await seed_arcade_words(db_session)  # seeds BUDGET, CREDIT, INCOME, ...

    mock_client = _mock_llm_client(json.dumps([]))  # response content irrelevant here
    with patch(
        "app.services.arcade_word_admin_service.get_llm_client",
        return_value=mock_client,
    ):
        await suggest_words(db_session, language="en")

    messages = mock_client.complete.call_args.args[1]
    user_content = messages[0]["content"]
    assert "do NOT return" in user_content
    assert "BUDGET" in user_content  # a seeded word appears in the avoid list


async def test_suggest_words_idempotent_on_second_call(db_session):
    """Running suggest_words twice with the same mock payload skips dupes."""
    await seed_arcade_words(db_session)

    mock_client = _mock_llm_client()
    with patch(
        "app.services.arcade_word_admin_service.get_llm_client",
        return_value=mock_client,
    ):
        first = await suggest_words(db_session, language="en")
        second = await suggest_words(db_session, language="en")

    assert first["created"] == 1
    assert second["created"] == 0   # GRANT now exists, gets skipped
