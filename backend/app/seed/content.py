from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Module, Lesson


_MODULES = [
    {
        "topic": "stocks", "title": "What is a Stock?",
        "country_codes": [], "is_premium": False, "order_index": 0,
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "A stock is a slice of a company",
                "body": "When you buy a stock, you own a tiny piece of that business. If the business does well, your piece can be worth more.",
            }},
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Why do people buy stocks?",
                "body": "Stocks can grow in value over time and some pay dividends — small cash payments to shareholders.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "If you own one stock in a company with 1,000,000 shares, what fraction of the company do you own?",
                "choices": ["1/100", "1/1,000,000", "1%", "All of it"],
                "answer_index": 1,
                "explanation": "One share out of one million is 1/1,000,000 of the company.",
            }},
        ],
    },
    {
        "topic": "savings", "title": "Compound Interest Basics",
        "country_codes": [], "is_premium": False, "order_index": 1,
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Interest on your interest",
                "body": "Compound interest means you earn interest not only on your original money, but also on the interest you've already earned.",
            }},
            {"type": "scenario", "xp_reward": 20, "content_json": {
                "prompt": "You deposit £100 at 5% annual interest. How much after 10 years?",
                "choices": [
                    {"label": "£150", "outcome": "Close — but that's simple interest."},
                    {"label": "£163", "outcome": "Correct! Compounding added £13 extra."},
                    {"label": "£200", "outcome": "Too high — compounding isn't that fast at 5%."},
                ],
                "correct_index": 1,
            }},
        ],
    },
    {
        "topic": "real_estate", "title": "What is a REIT?",
        "country_codes": [], "is_premium": False, "order_index": 2,
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Real Estate Investment Trust",
                "body": "A REIT is a company that owns income-producing property. You can buy shares like a stock to invest in property without buying a house.",
            }},
            {"type": "quiz", "xp_reward": 25, "content_json": {
                "question": "Which is true of REITs?",
                "choices": [
                    "You need £100,000 to buy into one",
                    "They let you invest in real estate via the stock market",
                    "They are only available in the US",
                ],
                "answer_index": 1,
                "explanation": "REITs trade on exchanges like stocks.",
            }},
        ],
    },
]


async def seed_modules_and_lessons(session: AsyncSession) -> None:
    """Idempotent: creates modules/lessons matched by (topic, title). Caller commits."""
    for spec in _MODULES:
        existing = await session.scalar(
            select(Module).where(Module.topic == spec["topic"], Module.title == spec["title"])
        )
        if existing:
            continue
        module = Module(
            topic=spec["topic"], title=spec["title"],
            country_codes=spec["country_codes"], is_premium=spec["is_premium"],
            order_index=spec["order_index"],
        )
        session.add(module)
        await session.flush()

        for idx, lesson_spec in enumerate(spec["lessons"]):
            session.add(Lesson(
                module_id=module.id, type=lesson_spec["type"],
                content_json=lesson_spec["content_json"],
                xp_reward=lesson_spec["xp_reward"], order_index=idx,
            ))
