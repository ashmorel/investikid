"""Offline-sync bundle assembly for the user's active market.

`build_bundle` loads the WHOLE active market in a few batch queries, serializes via
the shared content serializers (so the offline snapshot is byte-identical to the
per-item content routes), and assembles a delta'd response. `lessons` is the delta
(all when `since` is None, else `updated_at > since`); `modules`/`module_levels`/
`level_lessons`/`current_ids` are always the full current set. `server_time` comes
from the DB clock so it lines up with `updated_at` for the next `since`.

Market scoping mirrors the routes exactly via the shared `serialize_modules`
(visibility + age gate) — a module/lesson from another market never appears.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import today_utc
from app.models.content import (
    Lesson,
    LessonCompletion,
    Level,
    LevelMastery,
    Module,
)
from app.schemas.content import OfflineBundleIds, OfflineBundleOut
from app.services.content_localize import language_active, load_translations
from app.services.content_serialize import (
    serialize_lesson,
    serialize_lesson_summaries,
    serialize_levels,
    serialize_modules,
    user_age_for,
)


async def build_bundle(
    session: AsyncSession,
    current_user,
    since: datetime | None,
) -> OfflineBundleOut:
    market = current_user.active_market_code

    # Server clock — what the client stores as the next `since`. Taken from the DB
    # so it is comparable with the `updated_at` columns this bundle is delta'd on.
    server_time: datetime = await session.scalar(select(func.now()))

    user_age = user_age_for(current_user, today_utc())
    lang = current_user.language
    active = await language_active(session, lang)

    # --- Modules: published, ordered; serializer applies market + age gating. ---
    all_modules = list(await session.scalars(
        select(Module).where(Module.published.is_(True)).order_by(Module.order_index)
    ))
    module_translations = (
        await load_translations(session, "module", [m.id for m in all_modules], lang)
        if active else {}
    )
    modules = serialize_modules(
        current_user, all_modules, user_age=user_age,
        translations_active=active, module_translations=module_translations,
    )
    visible_module_ids = [m.id for m in modules]

    # Nothing visible → empty bundle (still a valid snapshot).
    if not visible_module_ids:
        return OfflineBundleOut(
            market=market, server_time=server_time.isoformat(),
            modules=[], module_levels={}, level_lessons={}, lessons=[],
            current_ids=OfflineBundleIds(),
        )

    # --- Levels for the visible modules. ---
    levels = list(await session.scalars(
        select(Level).where(Level.module_id.in_(visible_module_ids)).order_by(Level.order_index)
    ))
    levels_by_module: dict[uuid.UUID, list[Level]] = {}
    for lv in levels:
        levels_by_module.setdefault(lv.module_id, []).append(lv)

    # --- Lessons for the visible modules (full set for metadata + ids). ---
    all_lessons = list(await session.scalars(
        select(Lesson).where(Lesson.module_id.in_(visible_module_ids)).order_by(Lesson.order_index)
    ))
    lessons_by_module_for_levels: dict[uuid.UUID, dict[uuid.UUID, list[uuid.UUID]]] = {}
    lessons_by_level: dict[uuid.UUID, list[Lesson]] = {}
    for lsn in all_lessons:
        if lsn.level_id is not None:
            lessons_by_level.setdefault(lsn.level_id, []).append(lsn)
            lessons_by_module_for_levels.setdefault(lsn.module_id, {}).setdefault(
                lsn.level_id, []
            ).append(lsn.id)

    all_lesson_ids = [lsn.id for lsn in all_lessons]

    # --- Per-user state (loaded once). ---
    completed_ids: set[uuid.UUID] = set()
    scores: dict[uuid.UUID, float | None] = {}
    if all_lesson_ids:
        rows = (await session.execute(
            select(LessonCompletion.lesson_id, LessonCompletion.score).where(
                LessonCompletion.user_id == current_user.id,
                LessonCompletion.lesson_id.in_(all_lesson_ids),
            )
        )).all()
        for lid, score in rows:
            completed_ids.add(lid)
            scores[lid] = score

    level_ids = [lv.id for lv in levels]
    mastered_at_by_level: dict[uuid.UUID, object] = {}
    if level_ids:
        mastery_rows = (await session.execute(
            select(LevelMastery.level_id, LevelMastery.mastered_at).where(
                LevelMastery.user_id == current_user.id,
                LevelMastery.level_id.in_(level_ids),
            )
        )).all()
        mastered_at_by_level = dict(mastery_rows)

    lesson_translations = (
        await load_translations(session, "lesson", all_lesson_ids, lang)
        if active else {}
    )

    # --- module_levels (keyed by module id str) via the shared level serializer. ---
    module_levels: dict[str, list] = {}
    for mid in visible_module_ids:
        mod_levels = levels_by_module.get(mid, [])
        module_levels[str(mid)] = serialize_levels(
            current_user, mod_levels,
            lessons_by_level=lessons_by_module_for_levels.get(mid, {}),
            completed_ids=completed_ids, scores=scores,
            mastered_at_by_level=mastered_at_by_level,
        )

    # --- level_lessons (keyed by level id str) via the shared summary serializer. ---
    level_lessons: dict[str, list] = {}
    for lv in levels:
        level_lessons[str(lv.id)] = serialize_lesson_summaries(
            lessons_by_level.get(lv.id, []),
            completed_ids=completed_ids,
            translations_active=active, lesson_translations=lesson_translations,
        )

    # --- lessons delta (full LessonOut shape, same as get_lesson). ---
    delta_lessons = (
        all_lessons if since is None
        else [lsn for lsn in all_lessons if lsn.updated_at > since]
    )
    lessons = [
        serialize_lesson(
            lsn, completed=lsn.id in completed_ids,
            translations_active=active, translation=lesson_translations.get(lsn.id),
        )
        for lsn in delta_lessons
    ]

    current_ids = OfflineBundleIds(
        modules=[str(mid) for mid in visible_module_ids],
        levels=[str(lid) for lid in level_ids],
        lessons=[str(lid) for lid in all_lesson_ids],
    )

    return OfflineBundleOut(
        market=market,
        server_time=server_time.isoformat(),
        modules=modules,
        module_levels=module_levels,
        level_lessons=level_lessons,
        lessons=lessons,
        current_ids=current_ids,
    )
