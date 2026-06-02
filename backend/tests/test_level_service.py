import uuid

from app.services.level_service import LevelStateInput, derive_level_states


def _mk(order, *, premium=False, threshold=0.7):
    return LevelStateInput(
        level_id=uuid.uuid4(), order_index=order, is_premium=premium,
        pass_threshold=threshold,
    )


def test_first_level_unlocked_rest_locked_when_nothing_done():
    lvls = [_mk(0), _mk(1)]
    states = derive_level_states(
        lvls, lessons_by_level={lv.level_id: [uuid.uuid4()] for lv in lvls},
        completed_ids=set(), scores={}, user_is_premium=False,
    )
    s0, s1 = states[lvls[0].level_id], states[lvls[1].level_id]
    assert s0.state == "in_progress" and s0.locked_reason is None
    assert s1.state == "locked" and s1.locked_reason == "progression"


def test_passing_level1_unlocks_level2():
    l1, l2 = _mk(0, threshold=0.7), _mk(1)
    q = uuid.uuid4()  # one scored lesson in L1
    states = derive_level_states(
        [l1, l2], lessons_by_level={l1.level_id: [q], l2.level_id: [uuid.uuid4()]},
        completed_ids={q}, scores={q: 0.8}, user_is_premium=False,
    )
    assert states[l1.level_id].state == "completed"
    assert states[l1.level_id].passed is True
    assert states[l2.level_id].state == "in_progress"


def test_completed_but_not_passed_keeps_next_locked():
    l1, l2 = _mk(0, threshold=0.7), _mk(1)
    q = uuid.uuid4()
    states = derive_level_states(
        [l1, l2], lessons_by_level={l1.level_id: [q], l2.level_id: [uuid.uuid4()]},
        completed_ids={q}, scores={q: 0.5}, user_is_premium=False,
    )
    assert states[l1.level_id].passed is False
    assert states[l2.level_id].state == "locked"


def test_premium_level_shows_premium_lock_for_free_user():
    l1 = _mk(0, premium=True)
    states = derive_level_states(
        [l1], lessons_by_level={l1.level_id: [uuid.uuid4()]},
        completed_ids=set(), scores={}, user_is_premium=False,
    )
    assert states[l1.level_id].locked_reason == "premium"


def test_premium_precedence_over_progression():
    l1, l2 = _mk(0), _mk(1, premium=True)
    states = derive_level_states(
        [l1, l2], lessons_by_level={l1.level_id: [uuid.uuid4()], l2.level_id: [uuid.uuid4()]},
        completed_ids=set(), scores={}, user_is_premium=False,
    )
    # L2 is both progression-locked and premium → premium wins
    assert states[l2.level_id].locked_reason == "premium"


def test_appending_lesson_reverts_completed_level_to_in_progress():
    """Progress is computed live from total vs completed lessons, so adding a
    new lesson to a level the child already finished re-opens it and updates the
    counts — no stored state to migrate."""
    l1 = _mk(0)
    a, b = uuid.uuid4(), uuid.uuid4()

    done = derive_level_states(
        [l1], lessons_by_level={l1.level_id: [a, b]},
        completed_ids={a, b}, scores={}, user_is_premium=False,
    )[l1.level_id]
    assert done.state == "completed"
    assert (done.lessons_total, done.lessons_completed) == (2, 2)

    # A new (uncompleted) lesson is appended to the same level.
    c = uuid.uuid4()
    after = derive_level_states(
        [l1], lessons_by_level={l1.level_id: [a, b, c]},
        completed_ids={a, b}, scores={}, user_is_premium=False,
    )[l1.level_id]
    assert after.state == "in_progress"
    assert (after.lessons_total, after.lessons_completed) == (3, 2)
