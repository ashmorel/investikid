import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.services.admin_content_generation_service import (
    generate_native_level_lessons,
    target_lessons_for_tier,
)

logger = logging.getLogger(__name__)


def _nodes_by_level_id(proposal_json: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for mod in proposal_json.get("modules", []):
        for lvl in mod.get("levels", []):
            if lvl.get("level_id"):
                out[lvl["level_id"]] = lvl
    return out


async def generate_market_native(
    session: AsyncSession, module: Module, *, brief, proposal_row, include_populated: bool
) -> dict:
    nodes = _nodes_by_level_id(proposal_row.proposal_json)
    target_levels = (await session.execute(
        select(Level.id).where(Level.module_id == module.id).order_by(Level.order_index)
    )).all()
    summary = {"levels": [], "generated": 0, "skipped_populated": 0,
               "skipped_has_drafts": 0, "skipped_no_concepts": 0, "errored": 0}

    for (level_id,) in target_levels:
        entry = {"level_id": str(level_id), "status": "", "created": 0}
        node = nodes.get(str(level_id))
        concepts = (node or {}).get("concepts") or []
        if not concepts:
            entry["status"] = "skipped_no_concepts"
            summary["skipped_no_concepts"] += 1
            summary["levels"].append(entry)
            continue
        if not include_populated:
            lesson_n = await session.scalar(
                select(func.count(Lesson.id)).where(Lesson.level_id == level_id))
            if lesson_n:
                entry["status"] = "skipped_populated"
                summary["skipped_populated"] += 1
                summary["levels"].append(entry)
                continue
            draft_n = await session.scalar(
                select(func.count(LessonDraft.id)).where(LessonDraft.level_id == level_id))
            if draft_n:
                entry["status"] = "skipped_has_drafts"
                summary["skipped_has_drafts"] += 1
                summary["levels"].append(entry)
                continue
        try:
            level = await session.get(Level, level_id)
            tier = node.get("complexity_tier")
            result = await generate_native_level_lessons(
                session, level, brief=brief, concepts=concepts,
                complexity_tier=tier, target_count=target_lessons_for_tier(tier),
            )
            entry.update(status="generated", created=len(result.created))
            summary["generated"] += 1
        except Exception as exc:  # noqa: BLE001 — one level must not abort the module
            await session.rollback()
            logger.warning("native batch gen failed for level %s: %s", level_id, exc)
            entry["status"] = "error"
            summary["errored"] += 1
        summary["levels"].append(entry)
    return summary
