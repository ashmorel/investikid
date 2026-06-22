"""End-to-end market content pipeline, callable server-side (operator automation).

Replicates the admin Market-Content flow (brief → design → accept → generate →
approve → publish) as three resumable steps so a cron-gated endpoint can drive a
full market without the admin UI:

- ``scaffold_market``: ensure a verified brief, design a fresh curriculum, accept
  it (materialise staged modules/levels).
- ``generate_next_level``: generate + approve ONE staged level's lessons. Called
  in a loop until ``remaining == 0`` (kept per-level so each HTTP call is short).
- ``publish_market``: publish the accepted curriculum (swap live, archive old).

Authoring uses the Opus authoring tier; every lesson is moderation-checked during
generation. Lessons are generated at the tiered depth (10/15/20 per tier).
"""
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level, Module
from app.models.market import Market
from app.models.market_brief import MarketBrief
from app.services import investing_missions
from app.services.admin_content_generation_service import (
    generate_native_level_lessons,
    target_lessons_for_tier,
)
from app.services.lesson_approval_service import approve_level_drafts
from app.services.market_brief_service import generate_brief, require_verified_brief
from app.services.market_curriculum.curriculum_publish_service import (
    publish_market_curriculum,
)
from app.services.market_curriculum.designer import design_curriculum
from app.services.market_curriculum.proposal_service import (
    accept_proposal,
    get_proposal_for_generation,
    save_proposal,
)


async def _ensure_verified_brief(session: AsyncSession, market_code: str) -> MarketBrief:
    brief = (await session.scalars(
        select(MarketBrief).where(MarketBrief.market_code == market_code)
    )).first()
    if brief is None:
        market = await session.get(Market, market_code)
        if market is None:
            raise ValueError(f"unknown market {market_code}")
        brief = await generate_brief(session, market)
    if brief.status != "verified":
        # The operator pre-approved the generated brief for this run.
        brief.status = "verified"
        await session.flush()
    return brief


async def scaffold_market(session: AsyncSession, market_code: str) -> dict:
    """Verify a brief, design a fresh curriculum, accept it (staged). Supersedes
    any in-progress proposal for the market; a published one stays live until the
    new curriculum is published."""
    brief = await _ensure_verified_brief(session, market_code)
    # Discard any half-built staged curriculum (published=false, never archived,
    # never live) so a fresh design leaves no orphan modules — and a retried
    # scaffold call can't accumulate duplicates.
    staged = (await session.execute(
        select(Module.id).where(Module.market_code == market_code,
                                Module.published.is_(False), Module.archived_at.is_(None))
    )).scalars().all()
    if staged:
        await session.execute(delete(Lesson).where(Lesson.module_id.in_(staged)))
        await session.execute(delete(Module).where(Module.id.in_(staged)))
        await session.flush()
    proposal, report = await design_curriculum(market_code, brief.brief_json)
    row = await save_proposal(session, proposal, report)
    counts = await accept_proposal(session, row)
    await session.commit()
    return {"market": market_code, "stage": "scaffolded",
            "modules": counts["modules"], "levels": counts["levels"],
            "coverage_ok": report.ok}


def _nodes_by_level_id(proposal_json: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for mod in proposal_json.get("modules", []):
        for lvl in mod.get("levels", []):
            if lvl.get("level_id"):
                out[lvl["level_id"]] = lvl
    return out


async def generate_next_level(session: AsyncSession, market_code: str) -> dict:
    """Generate + approve the next staged level that has no published lessons yet.
    Returns ``remaining`` (levels still to do AFTER this one); 0 means done."""
    proposal = await get_proposal_for_generation(session, market_code)
    if proposal is None:
        raise ValueError(f"no accepted/published curriculum for {market_code}")
    brief = await require_verified_brief(session, market_code)
    nodes = _nodes_by_level_id(proposal.proposal_json)
    staged_ids = [uuid.UUID(m["module_id"])
                  for m in proposal.proposal_json.get("modules", []) if m.get("module_id")]

    level_rows = (await session.execute(
        select(Level.id).join(Module, Module.id == Level.module_id)
        .where(Module.id.in_(staged_ids), Module.published.is_(False))
        .order_by(Module.order_index, Level.order_index)
    )).scalars().all()
    pending = []
    for level_id in level_rows:
        n = await session.scalar(select(func.count(Lesson.id)).where(Lesson.level_id == level_id))
        if not n:
            pending.append(level_id)
    if not pending:
        return {"market": market_code, "stage": "generate", "remaining": 0}

    level_id = pending[0]
    level = await session.get(Level, level_id)
    node = nodes.get(str(level_id)) or {}
    concepts = node.get("concepts") or []
    tier = node.get("complexity_tier")
    result = await generate_native_level_lessons(
        session, level, brief=brief, concepts=concepts,
        complexity_tier=tier, target_count=target_lessons_for_tier(tier),
    )
    approved = await approve_level_drafts(session, level, replace=True)
    await session.commit()
    return {"market": market_code, "stage": "generate", "level_id": str(level_id),
            "drafts": len(result.created), "approved": approved.get("approved", 0),
            "remaining": len(pending) - 1}


async def publish_market(session: AsyncSession, market_code: str) -> dict:
    """Publish the accepted curriculum (atomic swap; retires + archives the old)."""
    result = await publish_market_curriculum(session, market_code)
    # Re-attach simulator missions to investing modules (the republish replaced the
    # lessons, cascade-deleting any prior missions).
    missions = await investing_missions.sync_investing_missions(session, market_code=market_code)
    await session.commit()
    return {"market": market_code, "stage": "published", "missions": missions, **result}
