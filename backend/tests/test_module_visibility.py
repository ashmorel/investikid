from types import SimpleNamespace

from app.services.content_service import is_module_visible


def _mod(market_code, published):
    return SimpleNamespace(market_code=market_code, published=published)


def test_published_in_market_is_visible():
    assert is_module_visible(_mod("GB", True), "GB") is True


def test_unpublished_is_hidden_even_in_market():
    assert is_module_visible(_mod("GB", False), "GB") is False


def test_published_wrong_market_is_hidden():
    assert is_module_visible(_mod("US", True), "GB") is False
