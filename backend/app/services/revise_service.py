from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import SpacedRepetitionItem, WeakConcept
from app.models.user import User, UserProgress
from app.services.ai_content_service import generate_practice_quiz
from app.services.content_service import record_daily_activity
from app.services.entitlements import is_premium
from app.services.spaced_repetition_service import get_due_items, record_review
from app.services.xp_service import record_xp

logger = logging.getLogger(__name__)

SESSION_CAP = 5
XP_PER_CORRECT = 5


def _concept_of(lesson: Lesson) -> str:
    """Same derivation the practice flow uses (ai.py practice_quiz)."""
    c = lesson.content_json or {}
    return c.get("question") or c.get("title") or c.get("prompt") or "general"


def encode_ref(
    *,
    kind: str,
    topic: str,
    lesson_id: uuid.UUID,
    concept: str,
    weak_concept_id: uuid.UUID | None,
) -> str:
    payload = {
        "kind": kind,
        "topic": topic,
        "lesson_id": str(lesson_id),
        "concept": concept,
        "weak_concept_id": str(weak_concept_id) if weak_concept_id else None,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_ref(ref: str) -> dict:
    try:
        raw = base64.urlsafe_b64decode(ref.encode())
        data = json.loads(raw)
        if data.get("kind") not in ("weak", "refresher") or "lesson_id" not in data:
            raise ValueError("bad ref payload")
        return data
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid ref") from exc


async def _lesson_for_concept(
    session: AsyncSession, *, topic: str, concept: str
) -> tuple[Lesson, Module] | None:
    """Find a lesson in `topic` whose derived concept equals `concept`."""
    rows = await session.execute(
        select(Lesson, Module).join(Module, Module.id == Lesson.module_id)
        .where(Module.topic == topic)
        .order_by(Lesson.order_index)  # deterministic when concept strings collide
    )
    for lesson, module in rows.all():
        if _concept_of(lesson) == concept:
            return lesson, module
    return None


async def _build_item(
    session, user, *, kind, lesson, module, concept, weak_concept_id=None
) -> dict | None:
    try:
        quiz = await generate_practice_quiz(
            session, lesson, user=user, topic=module.topic,
            concept=concept, premium=is_premium(user),
        )
    except Exception:  # noqa: BLE001
        logger.warning("revise: quiz generation failed for %s", lesson.id)
        return None
    return {
        "ref": encode_ref(kind=kind, topic=module.topic, lesson_id=lesson.id,
                          concept=concept, weak_concept_id=weak_concept_id),
        "kind": kind,
        "module_id": str(module.id),
        "lesson_id": str(lesson.id),
        "concept": concept,
        "question": quiz["question"],
        "choices": quiz["choices"],
    }


async def list_revisable_modules(session: AsyncSession, user: User) -> list[dict]:
    comp_modules = (await session.scalars(
        select(Module.id).distinct()
        .join(Lesson, Lesson.module_id == Module.id)
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(LessonCompletion.user_id == user.id)
    )).all()
    if not comp_modules:
        return []
    modules = (await session.scalars(
        select(Module).where(Module.id.in_(comp_modules))
    )).all()
    rows = (await session.execute(
        select(WeakConcept.topic, func.count(SpacedRepetitionItem.id))
        .join(SpacedRepetitionItem, SpacedRepetitionItem.weak_concept_id == WeakConcept.id)
        .where(
            SpacedRepetitionItem.user_id == user.id,
            SpacedRepetitionItem.next_review_at <= func.now(),
            WeakConcept.resolved == False,  # noqa: E712
        )
        .group_by(WeakConcept.topic)
    )).all()
    due_by_topic = {t: int(c) for t, c in rows}
    out = [{
        "module_id": str(m.id), "title": m.title, "icon": m.icon,
        "topic": m.topic, "due_weak_count": due_by_topic.get(m.topic, 0),
    } for m in modules]
    out.sort(key=lambda d: (-d["due_weak_count"], d["title"]))  # weak-first
    return out


async def build_session(
    session: AsyncSession, user: User, *, module_id: uuid.UUID | None
) -> list[dict]:
    items: list[dict] = []
    seen_concepts: set[tuple[str, str]] = set()

    # 1) Weak-first: due SR items -> weak concepts (already ordered by due-ness).
    due = await get_due_items(session, user.id)
    weak_ids = [d.weak_concept_id for d in due]
    if weak_ids:
        weaks = (await session.scalars(
            select(WeakConcept).where(WeakConcept.id.in_(weak_ids))
        )).all()
        by_id = {w.id: w for w in weaks}
        for d in due:  # preserve due order
            w = by_id.get(d.weak_concept_id)
            if not w:
                continue
            resolved = await _lesson_for_concept(session, topic=w.topic, concept=w.concept)
            if not resolved:
                continue
            lesson, module = resolved
            if module_id and module.id != module_id:
                continue
            item = await _build_item(session, user, kind="weak", lesson=lesson,
                                     module=module, concept=w.concept,
                                     weak_concept_id=w.id)
            if item:
                items.append(item)
                seen_concepts.add((module.topic, w.concept))
            if len(items) >= SESSION_CAP:
                return items

    # 2) Refresher top-up: completed lessons not already weak/seen.
    comp_q = (
        select(Lesson, Module, LessonCompletion.completed_at)
        .join(Module, Module.id == Lesson.module_id)
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(LessonCompletion.user_id == user.id)
        .order_by(LessonCompletion.completed_at.asc())  # stable rotation; oldest first
    )
    if module_id:
        comp_q = comp_q.where(Module.id == module_id)
    for lesson, module, _ in (await session.execute(comp_q)).all():
        concept = _concept_of(lesson)
        if (module.topic, concept) in seen_concepts:
            continue
        is_weak = await session.scalar(
            select(WeakConcept.id).where(
                WeakConcept.user_id == user.id, WeakConcept.topic == module.topic,
                WeakConcept.concept == concept, WeakConcept.resolved == False,  # noqa: E712
            )
        )
        if is_weak:
            continue
        item = await _build_item(session, user, kind="refresher", lesson=lesson,
                                 module=module, concept=concept)
        if item:
            items.append(item)
            seen_concepts.add((module.topic, concept))
        if len(items) >= SESSION_CAP:
            break
    return items


async def record_answer(
    session: AsyncSession, user: User, ref: str, selected_index: int
) -> dict:
    data = decode_ref(ref)
    lesson = await session.get(Lesson, uuid.UUID(data["lesson_id"]))
    if lesson is None:
        raise ValueError("lesson not found")
    quiz = await generate_practice_quiz(
        session, lesson, user=user, topic=data["topic"],
        concept=data["concept"], premium=is_premium(user),
    )
    answer_index = quiz["answer_index"]
    correct = selected_index == answer_index

    if data["kind"] == "weak" and data.get("weak_concept_id"):
        await record_review(session, user.id,
                            uuid.UUID(data["weak_concept_id"]), correct=correct)
    elif data["kind"] == "refresher" and not correct:
        wc = await session.scalar(
            select(WeakConcept).where(
                WeakConcept.user_id == user.id, WeakConcept.topic == data["topic"],
                WeakConcept.concept == data["concept"],
                WeakConcept.resolved == False,  # noqa: E712
            )
        )
        if wc is None:
            wc = WeakConcept(user_id=user.id, topic=data["topic"], concept=data["concept"])
            session.add(wc)
            await session.flush()
        await record_review(session, user.id, wc.id, correct=False)

    xp_awarded = 0
    goal_met = False
    if correct:
        progress = await session.get(UserProgress, user.id)
        if progress is None:
            progress = UserProgress(user_id=user.id)
            session.add(progress)
            await session.flush()
        today = datetime.now(UTC).date()
        xp = record_xp(progress, XP_PER_CORRECT, today=today)
        record_daily_activity(progress, today)
        xp_awarded = xp.awarded
        goal_met = xp.goal_met_now

    await session.commit()
    return {
        "correct": correct,
        "answer_index": answer_index,
        "explanation": quiz.get("explanation", ""),
        "xp_awarded": xp_awarded,
        "goal_met": goal_met,
    }
