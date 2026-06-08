import pytest

from app.schemas.admin import validate_lesson_content_json


def test_valid_card():
    validate_lesson_content_json("card", {"title": "T", "body": "B"})


def test_card_missing_body_raises():
    with pytest.raises(ValueError):
        validate_lesson_content_json("card", {"title": "T"})


def test_valid_quiz():
    validate_lesson_content_json("quiz", {
        "question": "Q", "choices": ["a", "b"], "answer_index": 1, "explanation": "E",
    })


def test_quiz_answer_index_out_of_range_raises():
    with pytest.raises(ValueError):
        validate_lesson_content_json("quiz", {
            "question": "Q", "choices": ["a", "b"], "answer_index": 5, "explanation": "E",
        })


def test_valid_scenario():
    validate_lesson_content_json("scenario", {
        "prompt": "P",
        "choices": [{"label": "a", "outcome": "o1"}, {"label": "b", "outcome": "o2"}],
        "correct_index": 0,
    })


def test_scenario_choice_missing_outcome_raises():
    with pytest.raises(ValueError):
        validate_lesson_content_json("scenario", {
            "prompt": "P", "choices": [{"label": "a"}], "correct_index": 0,
        })
