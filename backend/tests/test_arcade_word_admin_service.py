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

_VALID_WORD = "GRANT"          # 5 letters, new, not a seed word
_INVALID_LONG = "OVERFLOW1"   # 9 chars — must be skipped
_DUPLICATE = "SAVE"            # appears in the seed — must be skipped

_LLM_RESPONSE = json.dumps(
    [
        {"word": _VALID_WORD, "definition": "Money given to help pay for something without needing to be paid back."},
        {"word": _INVALID_LONG, "definition": "A word that is too long for our game."},
        {"word": _DUPLICATE, "definition": "Put money aside for the future."},
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
    assert result["skipped"] == 2  # too-long + duplicate

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
        [{"word": "YIELD", "definition": "How much a investment pays you back each year."}]
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
        select(ArcadeWord).where(ArcadeWord.word == "YIELD", ArcadeWord.language == "en")
    )
    assert row is None


async def test_suggest_words_skips_word_in_definition(db_session):
    """Word embedded in its own definition is rejected (answer leak)."""
    leak_response = json.dumps(
        [{"word": "LOAN", "definition": "A LOAN is money borrowed from a bank."}]
    )
    mock_client = _mock_llm_client(leak_response)
    with patch(
        "app.services.arcade_word_admin_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await suggest_words(db_session, language="en")

    assert result["created"] == 0
    assert result["skipped"] == 1


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
