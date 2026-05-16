from datetime import date

import pytest

from app.services.compliance import Regime, resolve_policy

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _dob_for_age(age: int, today: date) -> date:
    return date(today.year - age, today.month, today.day)


def test_gb_under_13_requires_consent():
    today = date(2026, 5, 16)
    p = resolve_policy("GB", _dob_for_age(12, today), today)
    assert p.regime is Regime.UK_AADC
    assert p.consent_age == 13
    assert p.requires_parental_consent is True
    assert p.email_verification_target == "parent"
    assert p.password_reset_mode == "parent"
    assert p.data_retention_days == 30
    assert p.profiling_default_off is True


def test_gb_13_does_not_require_consent():
    today = date(2026, 5, 16)
    p = resolve_policy("GB", _dob_for_age(13, today), today)
    assert p.requires_parental_consent is False
    assert p.email_verification_target == "self"
    assert p.password_reset_mode == "self"


def test_ie_under_16_requires_consent():
    today = date(2026, 5, 16)
    p = resolve_policy("IE", _dob_for_age(15, today), today)
    assert p.regime is Regime.EU_GDPRK
    assert p.consent_age == 16
    assert p.requires_parental_consent is True


def test_ie_16_does_not_require_consent():
    today = date(2026, 5, 16)
    p = resolve_policy("IE", _dob_for_age(16, today), today)
    assert p.requires_parental_consent is False


def test_us_under_13_is_coppa():
    today = date(2026, 5, 16)
    p = resolve_policy("US", _dob_for_age(12, today), today)
    assert p.regime is Regime.COPPA
    assert p.consent_age == 13
    assert p.requires_parental_consent is True


def test_hk_under_13_is_pdpo():
    today = date(2026, 5, 16)
    p = resolve_policy("HK", _dob_for_age(12, today), today)
    assert p.regime is Regime.HK_PDPO
    assert p.consent_age == 13


def test_unknown_country_defaults_to_13():
    today = date(2026, 5, 16)
    p = resolve_policy("ZZ", _dob_for_age(12, today), today)
    assert p.regime is Regime.DEFAULT
    assert p.consent_age == 13
    assert p.requires_parental_consent is True


def test_fr_under_13_is_eu_gdprk_age_13():
    today = date(2026, 5, 16)
    p = resolve_policy("FR", _dob_for_age(12, today), today)
    assert p.regime is Regime.EU_GDPRK
    assert p.consent_age == 13
    assert p.requires_parental_consent is True
