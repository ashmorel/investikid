import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Module
from app.models.market import Market
from app.services.market_curriculum.proposal_service import get_active_proposal


async def publish_market_curriculum(session: AsyncSession, market_code: str) -> dict:
    """Atomically swap a market's accepted-but-staged curriculum live: publish the
    staged modules, soft-retire the previously-published ones, flip has_content.
    Reversible (retire is a flag flip; rows are kept). Raises ValueError if there
    is no accepted proposal or a staged module has no published lessons."""
    row = await get_active_proposal(session, market_code)
    if row is None or row.status != "accepted":
        raise ValueError("no accepted curriculum to publish")

    staged_ids = [
        uuid.UUID(n["module_id"])
        for n in row.proposal_json.get("modules", [])
        if n.get("module_id")
    ]
    if not staged_ids:
        raise ValueError("accepted curriculum has no materialised modules")

    # Guard: every staged module must have at least one lesson. One grouped
    # query — a staged id absent from the result has zero lessons.
    with_lessons = set((await session.execute(
        select(Lesson.module_id)
        .where(Lesson.module_id.in_(staged_ids))
        .group_by(Lesson.module_id)
    )).scalars().all())
    if any(mid not in with_lessons for mid in staged_ids):
        raise ValueError("review and approve lessons before publishing")

    # Retire the currently-live modules for this market (excluding the staged set).
    retired = (await session.execute(
        update(Module)
        .where(Module.market_code == market_code, Module.published.is_(True),
               Module.id.notin_(staged_ids))
        .values(published=False, archived_at=datetime.now(UTC))
    )).rowcount or 0

    # Publish the staged modules.
    await session.execute(
        update(Module).where(Module.id.in_(staged_ids)).values(published=True)
    )

    market = await session.get(Market, market_code)
    if market is not None:
        market.has_content = True
    row.status = "published"
    await session.flush()
    return {"published": len(staged_ids), "retired": retired}
