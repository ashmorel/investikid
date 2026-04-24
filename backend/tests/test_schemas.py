import pytest
from datetime import date

from pydantic import ValidationError

from app.schemas.auth import RegisterRequest


def test_register_request_valid():
    req = RegisterRequest(
        email="kid@example.com",
        username="testKid",
        password="SecurePass123!",
        dob=date(2008, 3, 15),
        country_code="GB",
        currency_code="GBP",
        parent_email="parent@example.com",
    )
    assert req.email == "kid@example.com"


def test_register_requires_parent_email_under_18():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="kid@example.com",
            username="testKid",
            password="SecurePass123!",
            dob=date(2015, 1, 1),
            country_code="GB",
            currency_code="GBP",
            parent_email=None,
        )


def test_email_normalised_to_lowercase():
    req = RegisterRequest(
        email="Kid@Example.COM",
        username="testKid",
        password="SecurePass123!",
        dob=date(2008, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="parent@example.com",
    )
    assert req.email == "kid@example.com"
