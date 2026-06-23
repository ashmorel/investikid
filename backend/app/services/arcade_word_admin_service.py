"""LLM-assisted word-bank suggester for MoneyWord daily puzzles."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade_word import ArcadeWord
from app.services.guardrails import with_generation_framing
from app.services.llm_client import get_llm_client
from app.services.llm_json import extract_json_list
from app.services.moderation import moderate_output

_SYS = with_generation_framing(
    "You generate short finance vocabulary words for a kids' money-learning word game. "
    "Each item: an UPPERCASE common finance term 4-8 letters A-Z only (no spaces, hyphens, "
    "proper nouns, or plurals of a shorter root), plus a one-sentence kid-friendly definition "
    "(<=180 chars) that does NOT contain the word itself. Return a JSON array of "
    '{"word": "...", "definition": "..."}.'
)


def _valid_word(w: str) -> bool:
    return 4 <= len(w) <= 8 and w.isalpha() and w.isascii()


async def suggest_words(
    session: AsyncSession, *, language: str = "en", count: int = 10
) -> dict:
    raw = await get_llm_client("authoring").complete(
        _SYS,
        [{"role": "user", "content": f"Generate {count} words."}],
        temperature=0.5,
        max_tokens=1200,
        response_format="json",
    )
    items = extract_json_list(json.loads(raw))
    created = skipped = 0
    for it in items:
        word = str(it.get("word", "")).strip().upper()
        definition = str(it.get("definition", "")).strip()
        if (
            not _valid_word(word)
            or not definition
            or len(definition) > 180
            or word in definition.upper()
        ):
            skipped += 1
            continue
        exists = await session.scalar(
            select(ArcadeWord).where(
                ArcadeWord.word == word, ArcadeWord.language == language
            )
        )
        if exists is not None:
            skipped += 1
            continue
        mod = await moderate_output(definition, surface="lesson")
        if not mod.safe:
            skipped += 1
            continue
        session.add(
            ArcadeWord(
                word=word,
                definition=definition,
                language=language,
                length=len(word),
                status="pending",
                source="llm",
            )
        )
        created += 1
    await session.flush()
    return {"created": created, "skipped": skipped}
