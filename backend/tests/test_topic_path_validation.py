import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.content import TOPIC_PATH_VALUES
from app.schemas.user import UpdatePreferencesRequest


def test_topic_path_values_are_the_nine_module_topics():
    assert TOPIC_PATH_VALUES == frozenset({
        "stocks", "savings", "real_estate", "budgeting", "risk",
        "crypto", "taxes", "debt", "entrepreneurship",
    })


def test_preferences_accepts_valid_topic():
    assert UpdatePreferencesRequest(topic_path="crypto").topic_path == "crypto"


def test_preferences_empty_string_normalises_to_none():
    assert UpdatePreferencesRequest(topic_path="").topic_path is None


def test_preferences_none_stays_none():
    assert UpdatePreferencesRequest(topic_path=None).topic_path is None


def test_preferences_rejects_legacy_value():
    with pytest.raises(ValidationError):
        UpdatePreferencesRequest(topic_path="investing-101")


def test_register_rejects_invalid_topic_and_accepts_valid():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="a@b.com", username="kiddo", password="Abcd1234!xyz",
            dob="2014-01-01", country_code="GB", currency_code="GBP",
            topic_path="not-a-topic", policy_version_accepted="v1",
        )
    ok = RegisterRequest(
        email="a@b.com", username="kiddo", password="Abcd1234!xyz",
        dob="2014-01-01", country_code="GB", currency_code="GBP",
        topic_path="savings", policy_version_accepted="v1",
    )
    assert ok.topic_path == "savings"
