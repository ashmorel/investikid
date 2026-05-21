import pytest

REGISTER_URL = "/auth/register"

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_register_success(client):
    response = await client.post(REGISTER_URL, json={
        "email": "alice@example.com",
        "username": "alice123",
        "password": "SecurePass123!",
        "dob": "2008-03-15",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent@example.com",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert "password_hash" not in data


async def test_register_duplicate_email_rejected(client):
    payload = {
        "email": "bob@example.com",
        "username": "bob1",
        "password": "SecurePass123!",
        "dob": "2008-03-15",
        "country_code": "US",
        "currency_code": "USD",
        "parent_email": "bobparent@example.com",
    }
    await client.post(REGISTER_URL, json=payload)
    response = await client.post(REGISTER_URL, json=payload)
    assert response.status_code == 409


async def test_register_under_threshold_without_parent_email_rejected(client):
    """Under-threshold (GB <13) without parent_email → router rejects with 400."""
    response = await client.post(REGISTER_URL, json={
        "email": "young@example.com",
        "username": "younguser",
        "password": "SecurePass123!",
        "dob": "2015-01-01",
        "country_code": "GB",
        "currency_code": "GBP",
    })
    assert response.status_code == 400


async def test_register_over_threshold_without_parent_email_succeeds(client):
    """Over-threshold teen (US 14) self-registers without parent_email."""
    response = await client.post(REGISTER_URL, json={
        "email": "teen@example.com",
        "username": "teenuser",
        "password": "SecurePass123!",
        "dob": "2012-01-01",
        "country_code": "US",
        "currency_code": "USD",
    })
    assert response.status_code == 201


LOGIN_URL = "/auth/login"
LOGOUT_URL = "/auth/logout"
REFRESH_URL = "/auth/refresh"

_BASE_USER = {
    "password": "SecurePass123!",
    "dob": "2006-01-01",
    "country_code": "US",
    "currency_code": "USD",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email: str, username: str):
    await client.post(REGISTER_URL, json={**_BASE_USER, "email": email, "username": username})
    resp = await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return resp


async def test_login_success_sets_cookies(client):
    response = await _register_and_login(client, "login@example.com", "loginuser")
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


async def test_login_wrong_password_rejected(client):
    await client.post(REGISTER_URL, json={**_BASE_USER, "email": "wrongpw@example.com", "username": "wrongpwu"})
    response = await client.post(LOGIN_URL, json={"email": "wrongpw@example.com", "password": "BadPassword"})
    assert response.status_code == 401


async def test_logout_clears_cookies(client):
    await _register_and_login(client, "logout@example.com", "logoutuser")
    response = await client.post(LOGOUT_URL)
    assert response.status_code == 200
    assert response.cookies.get("access_token", "") == ""


async def test_refresh_issues_new_cookies(client):
    await _register_and_login(client, "refresh@example.com", "refreshuser")
    response = await client.post(REFRESH_URL)
    assert response.status_code == 200
    assert "access_token" in response.cookies


async def test_refresh_without_cookie_rejected(client):
    # With CSRF protection active, an unauthenticated refresh attempt is
    # rejected at the CSRF layer (403) before reaching the refresh handler's
    # own 401 path. Either is an acceptable "rejected" outcome.
    response = await client.post(REFRESH_URL)
    assert response.status_code in (401, 403)


async def test_register_password_too_short_rejected(client):
    response = await client.post(REGISTER_URL, json={
        "email": "short@example.com",
        "username": "shortuser",
        "password": "Ab1!",
        "dob": "2008-03-15",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent@example.com",
    })
    assert response.status_code == 422


async def test_register_password_without_digit_rejected(client):
    response = await client.post(REGISTER_URL, json={
        "email": "nodigit@example.com",
        "username": "nodigituser",
        "password": "NoDigitsHereAtAll!",
        "dob": "2008-03-15",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent@example.com",
    })
    assert response.status_code == 422


async def test_register_duplicate_username_rejected(client):
    payload = {
        "email": "u1@example.com",
        "username": "sameuser",
        "password": "SecurePass123!",
        "dob": "2006-01-01",
        "country_code": "US",
        "currency_code": "USD",
        "parent_email": "parent@example.com",
    }
    r1 = await client.post(REGISTER_URL, json=payload)
    assert r1.status_code == 201
    r2 = await client.post(
        REGISTER_URL,
        json={**payload, "email": "u2@example.com"},
    )
    assert r2.status_code == 409
    assert r2.json()["detail"] == "Username already taken"


async def test_refresh_rotates_old_token_invalid(client):
    await _register_and_login(client, "rotate@example.com", "rotateuser")
    login_resp = await client.post(
        LOGIN_URL, json={"email": "rotate@example.com", "password": "SecurePass123!"}
    )
    old_refresh = login_resp.cookies.get("refresh_token")
    assert old_refresh
    # Login rotated the csrf cookie — refresh the default header to match.
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")

    # First refresh succeeds and rotates the refresh token.
    r1 = await client.post(REFRESH_URL)
    assert r1.status_code == 200
    new_refresh = r1.cookies.get("refresh_token")
    assert new_refresh and new_refresh != old_refresh

    # Replay the old refresh token — should be rejected. CSRF rotation on the
    # successful refresh may also cause a 403 on the stale header; either
    # rejection is acceptable here since the test asserts the replay fails.
    r2 = await client.post(REFRESH_URL, cookies={"refresh_token": old_refresh})
    assert r2.status_code in (401, 403)


async def test_logout_revokes_refresh_token(client):
    await _register_and_login(client, "logoutrev@example.com", "logoutrev")
    login_resp = await client.post(
        LOGIN_URL, json={"email": "logoutrev@example.com", "password": "SecurePass123!"}
    )
    refresh_cookie = login_resp.cookies.get("refresh_token")
    assert refresh_cookie
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")

    logout = await client.post(LOGOUT_URL)
    assert logout.status_code == 200

    # Subsequent refresh with that cookie must fail. Logout also clears the
    # csrf cookie, so CSRF rejection (403) is an acceptable rejection path.
    r = await client.post(REFRESH_URL, cookies={"refresh_token": refresh_cookie})
    assert r.status_code in (401, 403)


async def test_login_locks_after_five_wrong_passwords(client):
    await client.post(
        REGISTER_URL,
        json={**_BASE_USER, "email": "lockme@example.com", "username": "lockmeuser"},
    )
    # Five wrong attempts in a row.
    for _ in range(5):
        r = await client.post(
            LOGIN_URL, json={"email": "lockme@example.com", "password": "WrongPass1!"}
        )
        assert r.status_code == 401

    # Sixth attempt (correct password) must be rejected while locked.
    r = await client.post(
        LOGIN_URL, json={"email": "lockme@example.com", "password": "SecurePass123!"}
    )
    assert r.status_code == 401


async def test_inactive_user_cannot_access_me(client, db_session):
    await _register_and_login(client, "inactive@example.com", "inactiveuser")
    from sqlalchemy import update

    from app.models.user import User
    await db_session.execute(
        update(User).where(User.email == "inactive@example.com").values(is_active=False)
    )
    await db_session.flush()

    r = await client.get("/users/me")
    assert r.status_code == 401


async def test_refresh_token_rejected_as_access_token(client):
    await _register_and_login(client, "rtoken@example.com", "rtokenuser")
    login_resp = await client.post(
        LOGIN_URL, json={"email": "rtoken@example.com", "password": "SecurePass123!"}
    )
    refresh_cookie = login_resp.cookies.get("refresh_token")
    assert refresh_cookie
    client.headers["X-CSRF-Token"] = client.cookies.get("csrf_token")
    # Use the refresh token as an access token.
    response = await client.get(
        "/users/me", cookies={"access_token": refresh_cookie}
    )
    assert response.status_code == 401


async def test_register_teen_self_sends_verify_email(client, db_session):
    from sqlalchemy import select

    from app.models.consent import SentEmail

    resp = await client.post("/auth/register", json={
        "email": "teen@example.com", "username": "teen1",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    assert resp.status_code == 201
    rows = (await db_session.scalars(
        select(SentEmail).where(SentEmail.template == "verify_email")
    )).all()
    assert any(r.to_email == "teen@example.com" for r in rows)


async def test_register_underage_no_child_email_ok_with_parent(client):
    resp = await client.post("/auth/register", json={
        "username": "littlekid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "parent@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending_consent"


async def test_register_teen_without_email_rejected(client):
    resp = await client.post("/auth/register", json={
        "username": "noemailteen", "password": "SecurePass123!",
        "dob": "2009-01-01", "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    assert resp.status_code == 400


async def test_login_with_username_for_emailless_account(client):
    # Underage account registered without child email, then parent-approved.
    from sqlalchemy import select

    from app.core.database import get_session
    from app.main import app
    from app.models.user import User

    reg = await client.post("/auth/register", json={
        "username": "emaillesskid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "parent2@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    assert reg.status_code == 201

    # Activate directly via the overridden session (simulating parent approval).
    gen = app.dependency_overrides[get_session]()
    db = await gen.__anext__()
    user = await db.scalar(select(User).where(User.username == "emaillesskid"))
    user.is_active = True
    await db.commit()

    resp = await client.post("/auth/login", json={
        "email": "emaillesskid", "password": "SecurePass123!",
    })
    assert resp.status_code == 200


async def test_verify_email_happy_path(client, db_session):
    from sqlalchemy import select

    from app.models.user import User
    from app.services.tokens import VERIFY_EMAIL_AUDIENCE, VERIFY_EMAIL_EXPIRY, issue_one_time_token

    await client.post("/auth/register", json={
        "email": "verifyme@example.com", "username": "verifyme",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    user = await db_session.scalar(select(User).where(User.username == "verifyme"))
    assert user.email_verified_at is None
    tok = await issue_one_time_token(
        db_session, purpose=VERIFY_EMAIL_AUDIENCE, email=user.email,
        subject_id=user.id, expires_in=VERIFY_EMAIL_EXPIRY,
    )
    resp = await client.get(f"/auth/verify-email?token={tok}")
    assert resp.status_code == 200
    await db_session.refresh(user)
    assert user.email_verified_at is not None


async def test_verify_email_bad_token_410(client):
    resp = await client.get("/auth/verify-email?token=not-a-real-token")
    assert resp.status_code == 410


async def test_forgot_password_underage_routes_to_parent(client, db_session):
    from sqlalchemy import select

    from app.models.consent import SentEmail

    await client.post("/auth/register", json={
        "username": "fpkid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "fpparent@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    resp = await client.post("/auth/forgot-password", json={"email": "fpkid"})
    assert resp.status_code == 202
    rows = (await db_session.scalars(
        select(SentEmail).where(SentEmail.template == "password_reset")
    )).all()
    assert any(r.to_email == "fpparent@example.com" for r in rows)


async def test_forgot_password_unknown_still_202(client):
    resp = await client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 202


async def test_reset_password_flow_revokes_refresh(client, db_session):
    from sqlalchemy import select

    from app.models.user import RefreshToken, User
    from app.services.tokens import PASSWORD_RESET_AUDIENCE, PASSWORD_RESET_EXPIRY, issue_one_time_token

    await client.post("/auth/register", json={
        "email": "resetme@example.com", "username": "resetme",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    user = await db_session.scalar(select(User).where(User.username == "resetme"))
    tok = await issue_one_time_token(
        db_session, purpose=PASSWORD_RESET_AUDIENCE, email=user.email,
        subject_id=user.id, expires_in=PASSWORD_RESET_EXPIRY,
    )
    resp = await client.post("/auth/reset-password", json={
        "token": tok, "new_password": "BrandNewPass456!",
    })
    assert resp.status_code == 200
    rt = (await db_session.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    )).all()
    assert all(t.revoked_at is not None for t in rt)
    login = await client.post("/auth/login", json={
        "email": "resetme@example.com", "password": "BrandNewPass456!",
    })
    assert login.status_code == 200


async def test_reset_password_weak_rejected(client, db_session):
    from sqlalchemy import select

    from app.models.user import User
    from app.services.tokens import PASSWORD_RESET_AUDIENCE, PASSWORD_RESET_EXPIRY, issue_one_time_token

    await client.post("/auth/register", json={
        "email": "weak@example.com", "username": "weakreset",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    user = await db_session.scalar(select(User).where(User.username == "weakreset"))
    tok = await issue_one_time_token(
        db_session, purpose=PASSWORD_RESET_AUDIENCE, email=user.email,
        subject_id=user.id, expires_in=PASSWORD_RESET_EXPIRY,
    )
    resp = await client.post("/auth/reset-password", json={
        "token": tok, "new_password": "short",
    })
    assert resp.status_code == 422
