"""CLI: python -m app.seed.run — seeds starter content (idempotent)."""
import asyncio
from app.core.database import async_session_factory
from app.seed.content import seed_modules_and_lessons


async def main() -> None:
    async with async_session_factory() as session:
        await seed_modules_and_lessons(session)
        await session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
