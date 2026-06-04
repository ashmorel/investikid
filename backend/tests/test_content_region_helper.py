from types import SimpleNamespace

from app.services.content_service import content_region_for


def test_content_region_falls_back_to_country_code_when_unset():
    user = SimpleNamespace(country_code="US", content_region=None)
    assert content_region_for(user) == "US"


def test_content_region_used_when_set():
    user = SimpleNamespace(country_code="US", content_region="HK")
    assert content_region_for(user) == "HK"


def test_content_region_falls_back_when_attribute_missing():
    # Defensive: objects without the attribute still resolve to country_code.
    user = SimpleNamespace(country_code="GB")
    assert content_region_for(user) == "GB"
