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
    "1. Each word MUST be a real, standard English dictionary word that is EITHER 5 OR 6 letters "
    "long. Count the letters; if it is not 5 or 6, leave it out.\n"
    "2. NEVER invent a word, NEVER truncate or chop a longer word to make it 5 or 6 letters, and "
    "NEVER pad or add letters to a shorter word. If a finance term is not naturally a real 5- or "
    "6-letter word, simply do not include it — return fewer words instead.\n"
    "3. The word must relate to money, saving, spending, banking, or investing, and be "
    "understandable by a 9-12 year old.\n"
    "4. UPPERCASE, A-Z only: no spaces, hyphens, accents, digits, proper nouns, abbreviations, "
    "or plurals of a shorter root.\n"
    "5. Add a one-sentence kid-friendly definition (<=180 chars) that does NOT contain the word "
    "itself.\n"
    'Return a JSON array of {"word": "...", "definition": "..."}. '
    "Use COMMON, well-known money words that any adult would recognise — not obscure jargon. "
    "Format examples only (do NOT simply return these): MONEY, PRICE, STOCK, WAGES, WALLET, "
    "MARKET, LENDER, SALARY."
)


# Curated allowlist of REAL, kid-appropriate money words (5-6 letters). The LLM
# proposes words + definitions, but only words in this set are accepted — this
# is the hard backstop that the prompt alone cannot provide: it rejects both
# truncated/invented non-words (e.g. "ACCRU" for ACCRUE) AND real-but-off-topic
# words, guaranteeing every banked word is a genuine money term. Extend this set
# to grow the bank's ceiling.
_MONEY_WORDS: frozenset[str] = frozenset({
    # ── 5 letters ──
    "MONEY", "COINS", "PENNY", "POUND", "PRICE", "VALUE", "WORTH", "COSTS",
    "SPEND", "SPENT", "SAVES", "EARNS", "DEBTS", "LOANS", "BONDS", "FUNDS",
    "STOCK", "TRADE", "WAGES", "YIELD", "NOTES", "CENTS", "CARDS", "BANKS",
    "VAULT", "TOTAL", "BILLS", "SALES", "BUYER", "GOODS", "REPAY", "CHEAP",
    "TAXES", "SHARE", "CHECK", "PURSE", "QUOTE", "OWNER", "ASSET",
    # ── 6 letters ──
    "BUDGET", "CREDIT", "INCOME", "INVEST", "PROFIT", "REFUND", "WALLET",
    "MARKET", "LENDER", "WEALTH", "BANKER", "SALARY", "POCKET", "EQUITY",
    "ESCROW", "BROKER", "COUPON", "CHARGE", "CHEQUE", "AMOUNT", "PAYDAY",
    "BORROW", "TRADER", "SELLER", "RICHES", "CHANGE", "SAVING", "EARNER",
    "ACCRUE", "DOLLAR", "TYCOON", "COSTLY", "THRIFT", "SAVERS", "FUNDED",
    "REPAID", "CASHED", "DEBITS", "EXPORT", "IMPORT", "RENTAL", "TENANT",
    "INSURE", "PRICED", "MARKUP", "PAYOUT", "SPENDS", "BUYERS",
})


def _valid_word(w: str) -> bool:
    """Accept only words on the curated money-word allowlist.

    Length/format are implied (every allowlist entry is a real 5-6 letter
    A-Z word). Gating on a known set — rather than just length/alpha — is what
    keeps truncated non-words like "ACCRU" and off-topic real words out of the
    bank, since the prompt alone cannot guarantee the model never miscounts."""
    return w in _MONEY_WORDS


async def suggest_words(
    session: AsyncSession, *, language: str = "en", count: int = 10
) -> dict:
    # The set of real, kid-friendly, 6-letter money words is small and the bank
    # already holds the obvious ones, so without an exclusion list the model
    # returns words we already have and every one is dedup-skipped (0 created).
    # Pass the existing words as an explicit "do not repeat" list and ask for
    # variety. Cap the list so the prompt can't grow unbounded as the bank fills.
    existing = (
        await session.scalars(
            select(ArcadeWord.word)
            .where(ArcadeWord.language == language)
            .order_by(ArcadeWord.created_at.desc())
            .limit(300)
        )
    ).all()
    avoid = ", ".join(sorted({w.upper() for w in existing}))
    user_msg = f"Generate {count} words."
    if avoid:
        user_msg += (
            f" We ALREADY have these — do NOT return any of them, pick different "
            f"words: {avoid}."
        )
    raw = await get_llm_client("authoring").complete(
        _SYS,
        [{"role": "user", "content": user_msg}],
        temperature=0.8,
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
