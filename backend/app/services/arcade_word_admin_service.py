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
    "You generate REAL English finance vocabulary words for a kids' money-learning word game "
    "(like Wordle). Follow EVERY rule:\n"
    "1. Each word MUST be a real, standard English dictionary word that is EXACTLY 6 letters "
    "long. Count the letters; if it is not exactly 6, leave it out.\n"
    "2. NEVER invent a word, NEVER truncate or chop a longer word to make it 6 letters, and "
    "NEVER pad or add letters to a shorter word. If a finance term is not naturally a real "
    "6-letter word, simply do not include it — return fewer words instead.\n"
    "3. The word must relate to money, saving, spending, banking, or investing, and be "
    "understandable by a 9-12 year old.\n"
    "4. UPPERCASE, A-Z only: no spaces, hyphens, accents, digits, proper nouns, abbreviations, "
    "or plurals of a shorter root.\n"
    "5. Add a one-sentence kid-friendly definition (<=180 chars) that does NOT contain the word "
    "itself.\n"
    'Return a JSON array of {"word": "...", "definition": "..."}. '
    "Examples of valid words: BUDGET, CREDIT, WALLET, INVEST, PROFIT, INCOME, SAVING, LENDER, "
    "MARKET, REFUND, WEALTH."
)


def _valid_word(w: str) -> bool:
    """Accept only an exact 6-letter ASCII word.

    The exact-6 rule is the hard backstop behind the prompt: it rejects any
    suggestion the model padded or truncated to a different length, so non-words
    produced by length-forcing never reach the bank. Real-word quality is then
    the prompt's job plus the human approval gate."""
    return len(w) == 6 and w.isalpha() and w.isascii()


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
