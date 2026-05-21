from datetime import date

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


def test_register_schema_allows_minor_without_parent_email():
    """Schema does NOT enforce parent_email; the /auth/register router enforces it
    only when the user is below the consent threshold (13, or 16 in select EU
    countries). Over-threshold teens self-register without a parent_email."""
    req = RegisterRequest(
        email="kid@example.com",
        username="testKid",
        password="SecurePass123!",
        dob=date(2012, 1, 1),  # over US threshold (13)
        country_code="US",
        currency_code="USD",
        parent_email=None,
    )
    assert req.parent_email is None


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


def test_register_request_email_optional_and_policy_field():
    from app.schemas.auth import RegisterRequest
    r = RegisterRequest(
        username="kid1", password="SecurePass123!", dob="2014-01-01",
        country_code="GB", currency_code="GBP", parent_email="p@example.com",
        policy_version_accepted="2026-05-16",
    )
    assert r.email is None
    assert r.policy_version_accepted == "2026-05-16"


def test_login_request_accepts_username_identifier():
    from app.schemas.auth import LoginRequest
    lr = LoginRequest(email="kiddo_username", password="whatever12345")
    # `email` field now carries an identifier (email OR username); not EmailStr.
    assert lr.email == "kiddo_username"
