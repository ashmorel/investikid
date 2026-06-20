from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.schemas.admin import validate_lesson_content_json
from app.services import llm_usage
from app.services.llm_client import get_llm_client, get_model_name
from app.services.moderation import moderate_output

logger = logging.getLogger(__name__)

_SCHEMA_HINT = {
    "card": '{"title": str, "body": str}',
    "quiz": '{"question": str, "choices": [str, str, ...(2-5)], "answer_index": int, "explanation": str}',
    "scenario": '{"prompt": str, "choices": [{"label": str, "outcome": str}, ...(>=2)], "correct_index": int}',
}


@dataclass
class GenerationResult:
    created: list[LessonDraft] = field(default_factory=list)
    skipped: int = 0


def _system_prompt(
    lesson_type: str,
    module: Module,
    level: Level,
    *,
    brief: dict | None = None,
    source_text: str | None = None,
) -> str:
    age = f"ages {module.min_age}-{module.max_age}" if module.min_age else "children 8-16"
    prompt = (
        f"You write a single financial-education {lesson_type} lesson for {age} on the topic "
        f"'{module.topic}' (module '{module.title}', '{level.title}'). Keep it simple, encouraging, "
        f"factual, and age-appropriate. Never give personalised financial advice. "
        f"Respond with ONLY a JSON object matching exactly: {_SCHEMA_HINT[lesson_type]}"
    )
    if brief is not None and source_text is not None:
        prompt += (
            f"\n\nADAPT the following GB (United Kingdom) lesson's concept into the target "
            f"market '{module.market_code}' using these verified market facts: "
            f"{json.dumps(brief, ensure_ascii=False)}. "
            f"Replace UK products, regulators, currency and examples with the market's real "
            f"equivalents from the facts above (e.g. ISA → the local tax-advantaged account, "
            f"FCA → the local regulator, £ → the local currency). Keep the learning objective, "
            f"structure and age level identical. Do not copy GB-specific names, regulators or "
            f"currency. Source lesson: {source_text}"
        )
    elif brief is not None and source_text is None:
        prompt += (
            f"\n\nWrite this as a MARKET-NATIVE lesson for the market '{module.market_code}', "
            f"grounded in these verified market facts: {json.dumps(brief, ensure_ascii=False)}. "
            f"Use the market's real products, regulators, currency and age-appropriate local "
            f"examples. This is NOT a UK lesson — do not reference UK-specific products, "
            f"regulators or currency."
        )
    return prompt


def _concat_text(parsed: dict) -> str:
    parts: list[str] = []
    for key in ("title", "body", "question", "explanation", "prompt"):
        if isinstance(parsed.get(key), str):
            parts.append(parsed[key])
    for ch in parsed.get("choices", []) or []:
        if isinstance(ch, str):
            parts.append(ch)
        elif isinstance(ch, dict):
            parts.extend(str(ch.get(k, "")) for k in ("label", "outcome"))
    return "\n".join(parts)


@llm_usage.surface("admin_content_gen")
async def _generate_one(session, *, level, module, concept: str, lesson_type: str,
                        brief: dict | None = None, source_text: str | None = None):
    client = get_llm_client("premium")
    system = _system_prompt(lesson_type, module, level, brief=brief, source_text=source_text)
    user = f"Create a {lesson_type} lesson teaching: {concept}."
    parsed = None
    for attempt in range(2):
        raw = await client.complete(
            system_prompt=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.4, max_tokens=700, response_format="json",
        )
        try:
            parsed = json.loads(raw)
            validate_lesson_content_json(lesson_type, parsed)
            break
        except (json.JSONDecodeError, ValueError, TypeError):
            parsed = None
            if attempt == 1:
                return None
    mod = await moderate_output(_concat_text(parsed), surface="lesson")
    draft = LessonDraft(
        level_id=level.id, type=lesson_type, content_json=parsed, concept=concept,
        model_used=get_model_name("premium"),
        moderation_safe=mod.safe, moderation_category=mod.category,
    )
    session.add(draft)
    if not mod.safe:
        session.add(AuditLog(
            user_id=None,
            event_type="moderation_block",
            metadata_json={"surface": "lesson", "category": mod.category},
        ))
    await session.flush()
    return draft


async def regenerate_draft(session: AsyncSession, draft: LessonDraft) -> LessonDraft | None:
    level = await session.get(Level, draft.level_id)
    module = await session.get(Module, level.module_id)
    fresh = await _generate_one(session, level=level, module=module, concept=draft.concept,
                                lesson_type=draft.type)
    if fresh is None:
        return None
    draft.content_json = fresh.content_json
    draft.moderation_safe = fresh.moderation_safe
    draft.moderation_category = fresh.moderation_category
    draft.model_used = fresh.model_used
    await session.delete(fresh)
    await session.commit()
    return draft


async def generate_level_lessons(session: AsyncSession, level, *, concept: str, count: int,
                                 types: list[str]) -> GenerationResult:
    module = await session.get(Module, level.module_id)
    result = GenerationResult()
    for i in range(count):
        lesson_type = types[i % len(types)]
        draft = await _generate_one(session, level=level, module=module, concept=concept,
                                    lesson_type=lesson_type)
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
    await session.commit()
    return result


async def generate_native_level_lessons(session: AsyncSession, level, *, brief, concepts,
                                        types: list[str] | None = None) -> GenerationResult:
    """Generate market-NATIVE lessons (brief-grounded, no GB source) for ``level``,
    one per concept. The caller passes a verified brief.
    """
    module = await session.get(Module, level.module_id)
    type_cycle = types or ["card", "quiz"]
    result = GenerationResult()
    for i, concept in enumerate(concepts):
        draft = await _generate_one(
            session, level=level, module=module, concept=concept,
            lesson_type=type_cycle[i % len(type_cycle)],
            brief=brief.brief_json, source_text=None,
        )
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
    await session.commit()
    return result


def _lesson_concept(lesson: Lesson) -> str:
    """Derive a short concept string from a source lesson's content."""
    content = lesson.content_json or {}
    for key in ("title", "question", "prompt"):
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:200]
    return lesson.type


async def generate_market_level_lessons(session: AsyncSession, target_level, *,
                                        source_level, brief) -> GenerationResult:
    """Adapt every lesson under ``source_level`` (GB) into ``target_level``'s market.

    Each generated draft is grounded in the verified ``brief`` and the GB lesson's
    text. The caller is responsible for passing a verified brief.
    """
    target_module = await session.get(Module, target_level.module_id)
    source_lessons = (await session.scalars(
        select(Lesson).where(Lesson.level_id == source_level.id).order_by(Lesson.order_index)
    )).all()
    result = GenerationResult()
    for src in source_lessons:
        # Only card/quiz/scenario are LLM-generatable. A GB level can also hold a
        # `video` lesson (curated YouTube) — skip those rather than crash trying
        # to build a prompt schema for a type we can't generate.
        if src.type not in _SCHEMA_HINT:
            result.skipped += 1
            continue
        draft = await _generate_one(
            session,
            level=target_level,
            module=target_module,
            concept=_lesson_concept(src),
            lesson_type=src.type,
            brief=brief.brief_json,
            source_text=_concat_text(src.content_json or {}),
        )
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
    await session.commit()
    return result


async def _gb_source_module(session, target_module: Module) -> Module | None:
    """Resolve the GB source module for a market module by the fields the scaffold
    preserves (topic + order_index). Returns None unless exactly one match."""
    rows = (await session.scalars(
        select(Module).where(
            Module.market_code == "GB",
            Module.topic == target_module.topic,
            Module.order_index == target_module.order_index,
        )
    )).all()
    return rows[0] if len(rows) == 1 else None


async def generate_module_market_lessons(
    session, target_module, *, brief, include_populated: bool
) -> dict:
    """Generate market drafts for every level in ``target_module``, resolving each
    level's GB source by order_index. Skips levels that already have lessons unless
    ``include_populated``. Best-effort per level (one failure never aborts the rest)."""
    gb_module = await _gb_source_module(session, target_module)
    # Capture identity as plain values up front: a per-level rollback (below)
    # expires ORM objects, so the loop must NOT touch attributes of cached
    # Level instances afterward — it re-`session.get`s fresh objects instead.
    target_levels = (await session.execute(
        select(Level.id, Level.order_index)
        .where(Level.module_id == target_module.id).order_by(Level.order_index)
    )).all()
    gb_by_order: dict[int, list] = {}
    if gb_module is not None:
        for src_id, src_order in (await session.execute(
            select(Level.id, Level.order_index).where(Level.module_id == gb_module.id)
        )).all():
            gb_by_order.setdefault(src_order, []).append(src_id)

    summary = {"levels": [], "generated": 0, "skipped_populated": 0,
               "skipped_no_source": 0, "errored": 0}
    for level_id, order_index in target_levels:
        entry = {"level_id": str(level_id), "status": "", "created": 0, "skipped": 0}
        src_ids = gb_by_order.get(order_index, [])
        if len(src_ids) != 1:
            entry["status"] = "skipped_no_source"
            summary["skipped_no_source"] += 1
            summary["levels"].append(entry)
            continue
        if not include_populated:
            count = await session.scalar(
                select(func.count(Lesson.id)).where(Lesson.level_id == level_id)
            )
            if count:
                entry["status"] = "skipped_populated"
                summary["skipped_populated"] += 1
                summary["levels"].append(entry)
                continue
        try:
            target_level = await session.get(Level, level_id)
            source_level = await session.get(Level, src_ids[0])
            result = await generate_market_level_lessons(
                session, target_level, source_level=source_level, brief=brief,
            )
            entry.update(status="generated", created=len(result.created), skipped=result.skipped)
            summary["generated"] += 1
        except Exception as exc:  # noqa: BLE001 — one level must not abort the module
            # Discard the failed level's flushed-but-uncommitted drafts so they
            # can't ride the NEXT level's commit into the DB. Safe to roll back:
            # the next iteration re-fetches its levels via session.get.
            await session.rollback()
            logger.warning("module batch gen failed for level %s: %s", level_id, exc)
            entry["status"] = "error"
            summary["errored"] += 1
        summary["levels"].append(entry)
    return summary
