"""Diagnostic items must be grounded in the target market (currency/locale), not
default to UK pounds. Pure unit tests for the prompt builder + the currency guard."""
from __future__ import annotations

from app.services.diagnostic_item_service import _build_system_prompt, _validate_candidate


def _candidate(question: str) -> dict:
    return {
        "question": question,
        "choices": ["A", "B", "C", "D"],
        "answer_index": 0,
        "explanation": "Because.",
    }


# --- prompt grounding -------------------------------------------------------


def test_prompt_grounds_market_and_currency():
    p = _build_system_prompt(
        market_code="HK", topic="saving", difficulty_tier=1, count=3,
        concept_slugs=[], market_name="Hong Kong", currency_code="HKD",
    )
    assert "Hong Kong" in p
    assert "HKD" in p
    # explicit anti-other-market-currency guard
    assert "NEVER use another market's currency" in p
    assert "ISAs" in p or "Premium Bonds" in p  # UK-residue products called out


def test_prompt_includes_brief_facts_when_present():
    p = _build_system_prompt(
        market_code="HK", topic="saving", difficulty_tier=1, count=2,
        concept_slugs=[], market_name="Hong Kong", currency_code="HKD",
        brief={"regulator": "HKMA", "currency": "HKD"},
    )
    assert "HKMA" in p


def test_prompt_grounds_even_without_market_record():
    # market lookup may be None — still must not silently default to UK
    p = _build_system_prompt(
        market_code="SG", topic="saving", difficulty_tier=1, count=2, concept_slugs=[],
    )
    assert "SG" in p
    assert "NEVER use another market's currency" in p


# --- currency-leak guard ----------------------------------------------------


def test_validate_rejects_pound_in_non_gb_market():
    assert _validate_candidate(_candidate("How much is £20 worth?"), market_code="HK") is None
    assert _validate_candidate(_candidate("You save 20 GBP a week."), market_code="US") is None


def test_validate_allows_pound_in_gb_market():
    assert _validate_candidate(_candidate("How much is £20 worth?"), market_code="GB") is not None


def test_validate_allows_local_currency_in_non_gb():
    # HK$ / plain $ must NOT be rejected for HK (only £/GBP are the UK-leak signal)
    assert _validate_candidate(_candidate("You have HK$50 to save."), market_code="HK") is not None


def test_validate_no_market_code_skips_guard():
    assert _validate_candidate(_candidate("A £5 note."), market_code=None) is not None
