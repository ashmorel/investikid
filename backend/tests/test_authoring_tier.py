from app.services import llm_client
from app.services.llm_client import (
    FallbackLLMClient,
    _strip_json_fences,
    get_llm_client,
    get_model_name,
)


def test_strip_json_fences():
    assert _strip_json_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _strip_json_fences('```\n[1, 2]\n```') == '[1, 2]'
    assert _strip_json_fences('{"a": 1}') == '{"a": 1}'


def _set(monkeypatch, **kw):
    for k, v in kw.items():
        monkeypatch.setattr(llm_client.settings, k, v)


def test_authoring_falls_back_to_premium_when_unset(monkeypatch):
    _set(monkeypatch, llm_authoring_api_key="", llm_authoring_model="",
         llm_premium_api_key="sk-x", llm_premium_provider="openai", llm_premium_model="gpt-5-mini")
    c = get_llm_client("authoring")
    assert isinstance(c, FallbackLLMClient)
    providers = [getattr(cl, "_provider", None) for cl in c.clients]
    assert "openai-premium" in providers
    assert "anthropic-authoring" not in providers


def test_authoring_uses_configured_model_first(monkeypatch):
    _set(monkeypatch, llm_authoring_api_key="ak-x", llm_authoring_model="claude-opus-4-8",
         llm_authoring_provider="anthropic", llm_premium_api_key="sk-x",
         llm_premium_provider="openai", llm_premium_model="gpt-5-mini")
    c = get_llm_client("authoring")
    assert isinstance(c, FallbackLLMClient)
    assert getattr(c.clients[0], "_provider", None) == "anthropic-authoring"  # authoring tried first
    assert get_model_name("authoring") == "claude-opus-4-8"
