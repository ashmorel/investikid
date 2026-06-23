"""Idempotent starter seed of approved English words for the MoneyWord daily puzzle."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade_word import ArcadeWord

# ~18 hand-verified finance terms, all 4-8 letters A-Z, approved for kids.
_WORDS: list[dict] = [
    {"word": "SAVE", "definition": "Put money aside now so you can use it for something important later."},
    {"word": "BUDGET", "definition": "A plan that shows how much money you have and how you will spend it."},
    {"word": "COIN", "definition": "A small round piece of metal used as money."},
    {"word": "BANK", "definition": "A safe place where people store their money and earn a little extra."},
    {"word": "DEBT", "definition": "Money that someone owes to another person or a business."},
    {"word": "ASSET", "definition": "Something valuable that you own, like money, a bike, or a house."},
    {"word": "INCOME", "definition": "Money you receive, for example from a job, allowance, or selling something."},
    {"word": "SPEND", "definition": "Use money to buy something you want or need."},
    {"word": "INVEST", "definition": "Put your money to work so it can grow into more money over time."},
    {"word": "STOCK", "definition": "A small piece of ownership in a company that you can buy or sell."},
    {"word": "INTEREST", "definition": "Extra money a bank pays you for saving, or you pay for borrowing."},
    {"word": "PROFIT", "definition": "The money left over after you have paid all your costs."},
    {"word": "WAGES", "definition": "Money paid to someone in return for the work they have done."},
    {"word": "CASH", "definition": "Physical money — the notes and coins you can hold in your hand."},
    {"word": "CREDIT", "definition": "Borrowing money now with a promise to pay it back later."},
    {"word": "REFUND", "definition": "Money returned to you when you send back something you bought."},
    {"word": "VALUE", "definition": "How much something is worth — the price others are willing to pay for it."},
    {"word": "TAXES", "definition": "Money people and businesses pay to the government to fund public services."},
]


async def seed_arcade_words(session: AsyncSession) -> int:
    """Insert approved starter words; skip any that already exist. Idempotent."""
    inserted = 0
    for entry in _WORDS:
        word = entry["word"]
        existing = await session.scalar(
            select(ArcadeWord).where(
                ArcadeWord.word == word, ArcadeWord.language == "en"
            )
        )
        if existing is not None:
            continue
        session.add(
            ArcadeWord(
                word=word,
                definition=entry["definition"],
                language="en",
                length=len(word),
                status="approved",
                source="manual",
            )
        )
        inserted += 1
    await session.flush()
    return inserted
