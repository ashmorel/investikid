"""CLI: python -m app.seed.run — seeds starter content (idempotent)."""
import asyncio

from app.core.database import async_session_factory
from app.seed.admin_bootstrap import bootstrap_admin
from app.seed.content import seed_modules_and_lessons
from app.seed.cosmetics import seed_cosmetics
from app.seed.gamification import seed_badges_and_challenges
from app.seed.markets import seed_markets
from app.seed.tier_accounts import seed_tier_accounts


async def main() -> None:
    async with async_session_factory() as session:
        await seed_markets(session)
        await seed_modules_and_lessons(session)
        await seed_badges_and_challenges(session)
        await seed_cosmetics(session)
        await seed_tier_accounts(session)
        await bootstrap_admin(session)
        await session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
