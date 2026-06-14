"""Unit tests for the LLM token-usage seam (M2 ops-hygiene)."""
import logging

from app.services import llm_usage


def test_record_usage_logs_surface_provider_and_totals(caplog):
    with caplog.at_level(logging.INFO, logger="llm.usage"):
        with llm_usage.track("coach"):
            llm_usage.record_usage(
                provider="together", model="llama-3", prompt_tokens=100, completion_tokens=40
            )
    assert "surface=coach" in caplog.text
    assert "provider=together" in caplog.text
    assert "prompt_tokens=100" in caplog.text
    assert "completion_tokens=40" in caplog.text
    assert "total_tokens=140" in caplog.text


def test_track_scopes_surface_and_resets():
    assert llm_usage.current_surface() == "unknown"
    with llm_usage.track("tutor"):
        assert llm_usage.current_surface() == "tutor"
    assert llm_usage.current_surface() == "unknown"  # resets on exit


def test_record_usage_never_raises_on_bad_input():
    # Telemetry must never break an LLM response.
    llm_usage.record_usage(provider="x", model="m", prompt_tokens=None, completion_tokens=None)
