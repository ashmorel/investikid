from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class LevelStateInput:
    level_id: uuid.UUID
    order_index: int
    is_premium: bool
    pass_threshold: float


@dataclass(frozen=True)
class LevelState:
    state: str            # "in_progress" | "completed" | "locked"
    locked_reason: str | None  # "premium" | "progression" | None
    passed: bool
    lessons_total: int
    lessons_completed: int


def _complete_and_passed(
    lesson_ids: list[uuid.UUID],
    completed_ids: set[uuid.UUID],
    scores: dict[uuid.UUID, float | None],
    threshold: float,
) -> tuple[bool, bool, int]:
    total = len(lesson_ids)
    done = sum(1 for lid in lesson_ids if lid in completed_ids)
    complete = total > 0 and done == total
    scored = [scores.get(lid) for lid in lesson_ids if scores.get(lid) is not None]
    if not scored:
        passed = complete  # no scored lessons → pass on completion
    else:
        passed = complete and (sum(scored) / len(scored)) >= threshold
    return complete, passed, done


def derive_level_states(
    levels: list[LevelStateInput],
    *,
    lessons_by_level: dict[uuid.UUID, list[uuid.UUID]],
    completed_ids: set[uuid.UUID],
    scores: dict[uuid.UUID, float | None],
    user_is_premium: bool,
) -> dict[uuid.UUID, LevelState]:
    ordered = sorted(levels, key=lambda lv: lv.order_index)
    out: dict[uuid.UUID, LevelState] = {}
    prev_passed = True  # the first level has no predecessor gate
    for lv in ordered:
        lesson_ids = lessons_by_level.get(lv.level_id, [])
        complete, passed, done = _complete_and_passed(
            lesson_ids, completed_ids, scores, lv.pass_threshold
        )
        progression_locked = not prev_passed
        if lv.is_premium and not user_is_premium:
            state, reason = "locked", "premium"
        elif progression_locked:
            state, reason = "locked", "progression"
        elif complete:
            state, reason = "completed", None
        else:
            state, reason = "in_progress", None
        out[lv.level_id] = LevelState(
            state=state, locked_reason=reason, passed=passed,
            lessons_total=len(lesson_ids), lessons_completed=done,
        )
        prev_passed = passed
    return out
