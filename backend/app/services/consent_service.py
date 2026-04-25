from datetime import date

EU_COUNTRIES_16: frozenset[str] = frozenset({"IE", "NL", "DE", "LU", "SK", "HR"})


def consent_threshold(country_code: str) -> int:
    """Age below which parental data-consent is required."""
    return 16 if country_code in EU_COUNTRIES_16 else 13


def age_in_years(dob: date, today: date) -> int:
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def needs_parental_consent(dob: date, country_code: str, today: date) -> bool:
    return age_in_years(dob, today) < consent_threshold(country_code)
