"""Single source of truth for child-facing content serialization.

The per-item content routes (`list_modules`, `list_levels`, `list_level_lessons`,
`get_lesson`) and the offline-sync bundle MUST produce byte-identical `ModuleOut`/
`LevelOut`/`LessonSummary`/`LessonOut` shapes. To guarantee that, the inline
Out-construction was extracted here so there is exactly ONE serializer, exercised
by both code paths. Each helper takes already-loaded ORM rows plus the per-user
state it needs (completion ids, scores, mastery map, translation maps) and returns
the Out objects — no DB access, no behaviour change.
"""

from __future__ import annotations

import uuid

from app.models.content import Lesson, Level, Module
from app.models.content_translation import ContentTranslation
from app.schemas.content import LessonOut, LessonSummary, LevelOut, ModuleOut
from app.services.age_tier import age_in_years
from app.services.content_localize import localize_fields
from app.services.content_service import (
    derive_lesson_title,
    is_module_age_ok,
    is_module_premium_ok,
    is_module_visible,
)
from app.services.entitlements import is_premium
from app.services.level_service import LevelStateInput, derive_level_states


def serialize_modules(
    current_user,
    modules: list[Module],
    *,
    user_age: int,
    translations_active: bool,
    module_translations: dict[uuid.UUID, ContentTranslation],
) -> list[ModuleOut]:
    """Serialize visible modules exactly as `list_modules` does.

    Out-of-market and out-of-age modules are omitted entirely; premium modules a
    free user can't access get `locked=True`; per-language title translation is
    applied when `translations_active`. Caller handles topic-path ordering.
    """
    user_is_premium = is_premium(current_user)
    out: list[ModuleOut] = []
    for m in modules:
        if not is_module_visible(m, current_user.active_market_code):
            continue
        # Hidden, not teased: out-of-age modules never appear in the list
        # (actual age from dob — the parent tier_override must not unlock these).
        if not is_module_age_ok(user_age, m.min_age, m.max_age):
            continue
        accessible = is_module_premium_ok(
            module_is_premium=m.is_premium, is_premium_user=user_is_premium
        )
        title = m.title
        machine_translated = False
        if translations_active:
            fields, machine_translated = localize_fields(
                "module", {"title": m.title}, module_translations.get(m.id)
            )
            title = fields["title"]
        out.append(ModuleOut(
            id=m.id, topic=m.topic, title=title,
            country_codes=m.country_codes, is_premium=m.is_premium,
            order_index=m.order_index, icon=m.icon, locked=not accessible,
            standards_alignment=m.standards_alignment, sources=m.sources,
            machine_translated=machine_translated,
        ))
    return out


def serialize_levels(
    current_user,
    levels: list[Level],
    *,
    lessons_by_level: dict[uuid.UUID, list[uuid.UUID]],
    completed_ids: set[uuid.UUID],
    scores: dict[uuid.UUID, float | None],
    mastered_at_by_level: dict[uuid.UUID, object],
) -> list[LevelOut]:
    """Serialize a module's levels exactly as `list_levels` does."""
    states = derive_level_states(
        [LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold) for lv in levels],
        lessons_by_level=lessons_by_level,
        completed_ids=completed_ids, scores=scores,
        user_is_premium=is_premium(current_user),
    )
    return [
        LevelOut(
            id=lv.id, module_id=lv.module_id, title=lv.title, order_index=lv.order_index,
            is_premium=lv.is_premium, icon=lv.icon,
            state=states[lv.id].state, locked_reason=states[lv.id].locked_reason,
            passed=states[lv.id].passed, lessons_total=states[lv.id].lessons_total,
            lessons_completed=states[lv.id].lessons_completed,
            learning_objectives=lv.learning_objectives,
            mastered_at=mastered_at_by_level.get(lv.id),
        )
        for lv in levels
    ]


def serialize_lesson_summaries(
    lessons: list[Lesson],
    *,
    completed_ids: set[uuid.UUID],
    translations_active: bool,
    lesson_translations: dict[uuid.UUID, ContentTranslation],
) -> list[LessonSummary]:
    """Serialize lessons into summaries exactly as `list_level_lessons` does."""
    summaries: list[LessonSummary] = []
    for lsn in lessons:
        content_json = lsn.content_json or {}
        machine_translated = False
        if translations_active:
            content_json, machine_translated = localize_fields(
                "lesson", content_json, lesson_translations.get(lsn.id)
            )
        summaries.append(LessonSummary(
            id=lsn.id, type=lsn.type,
            title=derive_lesson_title(lsn.type, content_json),
            xp_reward=lsn.xp_reward, order_index=lsn.order_index,
            completed=lsn.id in completed_ids,
            machine_translated=machine_translated,
        ))
    return summaries


def serialize_lesson(
    lesson: Lesson,
    *,
    completed: bool,
    translations_active: bool,
    translation: ContentTranslation | None,
) -> LessonOut:
    """Serialize a full lesson exactly as `get_lesson` does (always `locked=False`)."""
    content_json = lesson.content_json
    machine_translated = False
    if translations_active:
        content_json, machine_translated = localize_fields(
            "lesson", lesson.content_json or {}, translation
        )
    return LessonOut(
        id=lesson.id, module_id=lesson.module_id, type=lesson.type,
        content_json=content_json, xp_reward=lesson.xp_reward,
        order_index=lesson.order_index, completed=completed, locked=False,
        machine_translated=machine_translated,
    )


def user_age_for(current_user, today) -> int:
    """User's actual age in years (from dob) — the value `list_modules` gates on."""
    return age_in_years(current_user.dob, today)
