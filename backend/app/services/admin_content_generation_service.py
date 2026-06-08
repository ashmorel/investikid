from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.content import Level, Module
from app.models.lesson_draft import LessonDraft
from app.schemas.admin import validate_lesson_content_json
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


def _system_prompt(lesson_type: str, module: Module, level: Level) -> str:
    age = f"ages {module.min_age}-{module.max_age}" if module.min_age else "children 8-16"
    return (
        f"You write a single financial-education {lesson_type} lesson for {age} on the topic "
        f"'{module.topic}' (module '{module.title}', '{level.title}'). Keep it simple, encouraging, "
        f"factual, and age-appropriate. Never give personalised financial advice. "
        f"Respond with ONLY a JSON object matching exactly: {_SCHEMA_HINT[lesson_type]}"
    )


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


async def _generate_one(session, *, level, module, concept: str, lesson_type: str):
    client = get_llm_client("premium")
    system = _system_prompt(lesson_type, module, level)
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
