import uuid

from app.services.engagement_service import (
    LessonInput,
    compute_module_engagement,
)


def _lesson(t, **cj):
    return LessonInput(lesson_id=uuid.uuid4(), type=t, content_json=cj)


def test_per_lesson_counts_rate_score_and_completion_implies_view():
    mid = uuid.uuid4()
    q = _lesson("quiz", question="Q1")
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    result = compute_module_engagement(
        mid, [q],
        viewers_by_lesson={q.lesson_id: {u1, u2}},
        completers_by_lesson={q.lesson_id: {u2, u3}},
        scores_by_lesson={q.lesson_id: [0.5, 1.0]},
    )
    le = result.lessons[0]
    assert le.views == 3
    assert le.completions == 2
    assert le.completion_rate == 2 / 3
    assert le.average_score == 0.75
    assert le.label == "Q1"
    assert le.order == 0


def test_drop_off_uses_previous_lesson_completers():
    mid = uuid.uuid4()
    a, b = _lesson("card", title="A"), _lesson("quiz", question="B")
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    result = compute_module_engagement(
        mid, [a, b],
        viewers_by_lesson={a.lesson_id: {u1, u2, u3}, b.lesson_id: {u1}},
        completers_by_lesson={a.lesson_id: {u1, u2, u3}, b.lesson_id: {u1}},
        scores_by_lesson={},
    )
    assert result.lessons[0].drop_off == 0
    assert result.lessons[1].drop_off == 2


def test_module_summary_started_completed_and_rate():
    mid = uuid.uuid4()
    a, b = _lesson("card", title="A"), _lesson("quiz", question="B")
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    result = compute_module_engagement(
        mid, [a, b],
        viewers_by_lesson={a.lesson_id: {u1, u2, u3}, b.lesson_id: {u1, u2}},
        completers_by_lesson={a.lesson_id: {u1, u2}, b.lesson_id: {u1}},
        scores_by_lesson={},
    )
    assert result.learners_started == 3
    assert result.learners_completed == 1
    assert result.completion_rate == 1 / 3


def test_zero_views_lesson_has_none_rate_no_divide_by_zero():
    mid = uuid.uuid4()
    a = _lesson("video", youtube_id="x", caption="Intro")
    result = compute_module_engagement(
        mid, [a],
        viewers_by_lesson={}, completers_by_lesson={}, scores_by_lesson={},
    )
    le = result.lessons[0]
    assert le.views == 0
    assert le.completion_rate is None
    assert le.average_score is None
    assert le.label == "Intro"


def test_empty_module_is_all_zeros_none():
    mid = uuid.uuid4()
    result = compute_module_engagement(mid, [], {}, {}, {})
    assert result.lessons == []
    assert result.learners_started == 0
    assert result.learners_completed == 0
    assert result.completion_rate is None
    assert result.average_score is None
