import pytest
from pydantic import ValidationError

from app.schemas.admin import LessonCreate


def test_card_lesson_valid():
    lesson = LessonCreate(type="card", content_json={"title": "Test", "body": "Body text"}, xp_reward=10, order_index=0)
    assert lesson.content_json["title"] == "Test"


def test_card_lesson_missing_body():
    with pytest.raises(ValidationError, match="Card requires.*body"):
        LessonCreate(type="card", content_json={"title": "Test"}, xp_reward=10, order_index=0)


def test_quiz_lesson_valid():
    lesson = LessonCreate(type="quiz", content_json={"question": "Q?", "choices": ["A", "B", "C"], "answer_index": 1, "explanation": "Because B"}, xp_reward=25, order_index=0)
    assert lesson.type == "quiz"


def test_quiz_lesson_too_few_choices():
    with pytest.raises(ValidationError, match="at least 2 choices"):
        LessonCreate(type="quiz", content_json={"question": "Q?", "choices": ["A"], "answer_index": 0, "explanation": "Exp"}, xp_reward=25, order_index=0)


def test_quiz_lesson_invalid_answer_index():
    with pytest.raises(ValidationError, match="answer_index"):
        LessonCreate(type="quiz", content_json={"question": "Q?", "choices": ["A", "B"], "answer_index": 5, "explanation": "Exp"}, xp_reward=25, order_index=0)


def test_scenario_lesson_valid():
    lesson = LessonCreate(type="scenario", content_json={"prompt": "Scenario prompt", "choices": [{"label": "A", "outcome": "Result A"}, {"label": "B", "outcome": "Result B"}], "correct_index": 0}, xp_reward=20, order_index=0)
    assert lesson.type == "scenario"


def test_scenario_lesson_missing_outcome():
    with pytest.raises(ValidationError, match="label.*outcome"):
        LessonCreate(type="scenario", content_json={"prompt": "P", "choices": [{"label": "A"}, {"label": "B"}], "correct_index": 0}, xp_reward=20, order_index=0)
