from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Literal

from app.services.consent_service import EU_COUNTRIES_16, age_in_years

_EU_GDPRK_COUNTRIES: frozenset[str] = frozenset({
    "IE", "NL", "DE", "LU", "SK", "HR", "FR", "ES", "IT", "BE", "AT",
    "PT", "PL", "SE", "DK", "FI", "CZ", "HU", "RO", "BG", "GR", "EE",
    "LV", "LT", "SI", "CY", "MT",
})


class Regime(StrEnum):
    UK_AADC = "UK_AADC"
    COPPA = "COPPA"
    EU_GDPRK = "EU_GDPRK"
    HK_PDPO = "HK_PDPO"
    DEFAULT = "DEFAULT"


@dataclass(frozen=True)
class CompliancePolicy:
    regime: Regime
    consent_age: int
    requires_parental_consent: bool
    email_verification_target: Literal["parent", "self"]
    password_reset_mode: Literal["parent", "self"]
    data_retention_days: int
    profiling_default_off: bool


def _regime_for(country_code: str) -> Regime:
    cc = country_code.upper()
    if cc == "GB":
        return Regime.UK_AADC
    if cc == "US":
        return Regime.COPPA
    if cc == "HK":
        return Regime.HK_PDPO
    if cc in _EU_GDPRK_COUNTRIES:
        return Regime.EU_GDPRK
    return Regime.DEFAULT


def _consent_age_for(country_code: str, regime: Regime) -> int:
    if regime is Regime.EU_GDPRK and country_code.upper() in EU_COUNTRIES_16:
        return 16
    return 13


def resolve_policy(country_code: str, dob: date, today: date) -> CompliancePolicy:
    regime = _regime_for(country_code)
    consent_age = _consent_age_for(country_code, regime)
    needs_consent = age_in_years(dob, today) < consent_age
    target = "parent" if needs_consent else "self"
    return CompliancePolicy(
        regime=regime,
        consent_age=consent_age,
        requires_parental_consent=needs_consent,
        email_verification_target=target,
        password_reset_mode=target,
        data_retention_days=30,
        profiling_default_off=True,
    )
