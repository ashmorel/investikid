from fastapi import HTTPException

from app.services.premium_config import (
    PREMIUM_BENEFITS,
    PREMIUM_REQUEST_COOLDOWN_HOURS,
    premium_required_error,
)


def test_benefits_nonempty_strings():
    assert PREMIUM_BENEFITS and all(isinstance(b, str) and b for b in PREMIUM_BENEFITS)


def test_cooldown_positive():
    assert PREMIUM_REQUEST_COOLDOWN_HOURS > 0


def test_premium_required_error_shape():
    err = premium_required_error("level", "Investing Basics")
    assert isinstance(err, HTTPException)
    assert err.status_code == 403
    assert err.detail == {
        "message": "Premium required",
        "code": "premium_required",
        "context": {"kind": "level", "label": "Investing Basics"},
    }
