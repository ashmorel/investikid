"""Quiz Rush service: build a question set and score a submission server-side."""
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.markets import active_market
from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import ConceptMastery
from app.models.user import User

COLD_START_MIN = 10
# A concept the child has attempted but scores below this (correct/attempts) is a
# gap. Quiz Rush prioritises lessons on these concepts so play reinforces weaknesses
# instead of serving random trivia — the arcade-subordination rule (B3).
WEAK_CONCEPT_THRESHOLD = 0.6


def _shuffle(seq: list) -> list:
    items = list(seq)
    for i in range(len(items) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def _to_item(lesson: Lesson) -> dict:
    cj = lesson.content_json or {}
    return {
        "lesson_id": str(lesson.id),
        "question": cj.get("question", ""),
        "choices": list(cj.get("choices", [])),
        "answer_index": int(cj.get("answer_index", 0)),
    }


async def build_session(session: AsyncSession, user: User, *, limit: int = 20) -> list[dict]:
    """Return a shuffled list of quiz items for the child.

    Prefers quiz lessons in modules where the child has a LessonCompletion
    (i.e. they have started unlocking concepts in that module) in their active
    market.  If that pool has fewer than COLD_START_MIN items, falls back to
    ALL published, non-archived quiz lessons in the active market.
    """
    market = active_market(user)

    unlocked_ids = (await session.scalars(
        select(Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
        .where(
            LessonCompletion.user_id == user.id,
            Lesson.type == "quiz",
            Module.market_code == market,
            Module.archived_at.is_(None),
            Module.published.is_(True),
        )
        .distinct()
    )).all()

    unlocked = (await session.scalars(
        select(Lesson).where(Lesson.id.in_(unlocked_ids))
    )).all() if unlocked_ids else []

    pool = list(unlocked)

    if len(pool) < COLD_START_MIN:
        pool = (await session.scalars(
            select(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Lesson.type == "quiz",
                Module.market_code == market,
                Module.archived_at.is_(None),
                Module.published.is_(True),
            )
        )).all()

    # Reinforce gaps: surface lessons on the child's weak concepts first, then fill
    # the rest with the remaining pool (both shuffled for variety).
    weak_ids = await _weak_concept_ids(session, user.id)
    if weak_ids:
        weak = [le for le in pool if le.concept_id in weak_ids]
        rest = [le for le in pool if le.concept_id not in weak_ids]
        ordered = _shuffle(weak) + _shuffle(rest)
    else:
        ordered = _shuffle(list(pool))

    return [_to_item(le) for le in ordered[:limit]]


async def _weak_concept_ids(session: AsyncSession, user_id) -> set:
    """Concepts the child has attempted but not yet mastered (a gap to reinforce)."""
    rows = await session.scalars(
        select(ConceptMastery.concept_id).where(
            ConceptMastery.user_id == user_id,
            ConceptMastery.attempts > 0,
            ConceptMastery.mastery_score < WEAK_CONCEPT_THRESHOLD,
        )
    )
    return set(rows.all())


def score_submission(session_items: list[dict], answers: list[dict]) -> dict:
    """Pure authoritative scoring function.

    Args:
        session_items: The items returned by build_session (contains answer_index).
        answers: Client submission — list of {"lesson_id": str, "choice_index": int}.

    Returns:
        {"correct": int, "max_combo": int, "points": int}
        where points = correct*10 + max_combo*5 and combo = longest consecutive
        run of correct answers in submitted order.  Unknown lesson_ids count as wrong.
    """
    key = {it["lesson_id"]: it["answer_index"] for it in session_items}
    correct = combo = max_combo = 0
    for ans in answers:
        lid = ans.get("lesson_id")
        if lid in key and ans.get("choice_index") == key[lid]:
            correct += 1
            combo += 1
            max_combo = max(max_combo, combo)
        else:
            combo = 0
    return {"correct": correct, "max_combo": max_combo, "points": correct * 10 + max_combo * 5}
