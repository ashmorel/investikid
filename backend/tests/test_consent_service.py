from datetime import date

from app.services.consent_service import (
    age_in_years, consent_threshold, needs_parental_consent,
)


def test_age_basic():
    assert age_in_years(date(2010, 1, 1), date(2026, 1, 1)) == 16


def test_age_birthday_not_yet():
    assert age_in_years(date(2010, 6, 15), date(2026, 6, 14)) == 15


def test_threshold_ireland():
    assert consent_threshold("IE") == 16


def test_threshold_uk():
    assert consent_threshold("GB") == 13


def test_needs_consent_under_uk_13():
    assert needs_parental_consent(date(2014, 1, 1), "GB", date(2026, 4, 25)) is True


def test_no_consent_uk_14():
    assert needs_parental_consent(date(2012, 1, 1), "GB", date(2026, 4, 25)) is False


def test_needs_consent_ireland_15():
    assert needs_parental_consent(date(2011, 1, 1), "IE", date(2026, 4, 25)) is True


def test_no_consent_ireland_16():
    assert needs_parental_consent(date(2010, 1, 1), "IE", date(2026, 4, 25)) is False
