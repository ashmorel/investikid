"""Diagnostic items must be grounded in the target market (currency/locale), not
default to UK pounds. Pure unit tests for the prompt builder + the currency guard."""
from __future__ import annotations

import pytest

from app.services.diagnostic_item_service import _build_system_prompt, _validate_candidate

# The 10 markets and the currency each must ground in. Mirrors app/seed/markets.py;
# this is the contract the prompt depends on (Use {currency_code} …).
_EXPECTED_CURRENCIES = {
    "GB": "GBP", "US": "USD", "AU": "AUD", "CA": "CAD", "IE": "EUR",
    "ES": "EUR", "FR": "EUR", "DE": "EUR", "HK": "HKD", "SG": "SGD",
}


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


# --- cross-currency guard (word-boundary, all markets) ----------------------


def test_validate_rejects_foreign_currency_code():
    # HK (HKD) item leaking another market's code → dropped
    assert _validate_candidate(_candidate("You earn 50 USD."), market_code="HK", currency_code="HKD") is None
    assert _validate_candidate(_candidate("Costs 10 EUR."), market_code="HK", currency_code="HKD") is None
    # Ireland (EUR) leaking USD → dropped
    assert _validate_candidate(_candidate("Save 20 USD."), market_code="IE", currency_code="EUR") is None


def test_validate_allows_own_currency_code():
    assert _validate_candidate(_candidate("You have 50 HKD / HK$50."), market_code="HK", currency_code="HKD") is not None
    assert _validate_candidate(_candidate("Costs 10 EUR."), market_code="IE", currency_code="EUR") is not None
    assert _validate_candidate(_candidate("Save 20 USD."), market_code="US", currency_code="USD") is not None


def test_validate_word_boundary_no_false_positives():
    # "AUD" in fraud, "CAD" in decade, "EUR" in Europe must NOT trip the guard
    for word in ("Avoiding fraud is smart.", "Over a decade of saving.", "Banks across Europe."):
        assert _validate_candidate(_candidate(word), market_code="HK", currency_code="HKD") is not None


# --- every market grounds in its real currency ------------------------------


def test_market_seed_currencies_match_contract():
    """Guard the source of truth: a seed typo would silently mis-ground a market."""
    from app.seed.markets import MARKETS

    seeded = {m["code"]: m["currency_code"] for m in MARKETS}
    assert seeded == _EXPECTED_CURRENCIES


@pytest.mark.parametrize("code,currency", sorted(_EXPECTED_CURRENCIES.items()))
def test_prompt_grounds_each_market_currency(code, currency):
    p = _build_system_prompt(
        market_code=code, topic="saving", difficulty_tier=1, count=2,
        concept_slugs=[], market_name=code, currency_code=currency,
    )
    assert f"Use {currency} for ALL money amounts" in p
    assert "NEVER use another market's currency" in p
