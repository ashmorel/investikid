"""Pure unit tests for first_actionable_lesson (no async, no db)."""
import uuid

from app.services.level_service import LevelStateInput, first_actionable_lesson


def _lvl(order, *, premium=False, threshold=0.7):
    return LevelStateInput(uuid.uuid4(), order, premium, threshold)


def test_first_in_progress_level_first_incomplete_lesson():
    l1, l2 = _lvl(0), _lvl(1)
    a1, a2 = uuid.uuid4(), uuid.uuid4()
    b1 = uuid.uuid4()
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1, a2], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.9},
        user_is_premium=False,
    )
    assert result == (l1.level_id, a2)


def test_skips_to_second_level_when_first_complete_and_passed():
    l1, l2 = _lvl(0), _lvl(1)
    a1 = uuid.uuid4()
    b1 = uuid.uuid4()
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.9},  # passes threshold -> level 1 completed+passed
        user_is_premium=False,
    )
    assert result == (l2.level_id, b1)


def test_never_points_into_premium_locked_level():
    l1, l2 = _lvl(0), _lvl(1, premium=True)
    a1 = uuid.uuid4()
    b1 = uuid.uuid4()
    # level 1 fully complete+passed, level 2 premium-locked for a free user
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.9},
        user_is_premium=False,
    )
    assert result is None


def test_progression_locked_when_prev_not_passed():
    l1, l2 = _lvl(0), _lvl(1)
    a1 = uuid.uuid4()
    b1 = uuid.uuid4()
    # level 1 complete but FAILED (score below threshold) -> level 2 progression-locked,
    # and level 1 is "completed" (not in_progress) -> nothing actionable
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.1},
        user_is_premium=False,
    )
    assert result is None


def test_premium_user_can_enter_premium_level():
    l1, l2 = _lvl(0), _lvl(1, premium=True)
    a1 = uuid.uuid4()
    b1 = uuid.uuid4()
    result = first_actionable_lesson(
        [l1, l2],
        lessons_by_level_ordered={l1.level_id: [a1], l2.level_id: [b1]},
        completed_ids={a1},
        scores={a1: 0.9},
        user_is_premium=True,
    )
    assert result == (l2.level_id, b1)


def test_returns_none_when_no_lessons():
    l1 = _lvl(0)
    result = first_actionable_lesson(
        [l1],
        lessons_by_level_ordered={l1.level_id: []},
        completed_ids=set(),
        scores={},
        user_is_premium=False,
    )
    assert result is None
