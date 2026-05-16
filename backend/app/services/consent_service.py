from datetime import date

# Kept for backwards-compatible imports (used elsewhere).
EU_COUNTRIES_16: frozenset[str] = frozenset({"IE", "NL", "DE", "LU", "SK", "HR"})


def age_in_years(dob: date, today: date) -> int:
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def consent_threshold(country_code: str) -> int:
    """Age below which parental data-consent is required."""
    # Imported here to avoid a circular import (compliance imports age_in_years).
    from app.services.compliance import _consent_age_for, _regime_for
    return _consent_age_for(country_code, _regime_for(country_code))


def needs_parental_consent(dob: date, country_code: str, today: date) -> bool:
    from app.services.compliance import resolve_policy
    return resolve_policy(country_code, dob, today).requires_parental_consent
