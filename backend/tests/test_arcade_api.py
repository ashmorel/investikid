import pytest

from app.models.arcade_word import ArcadeWord

pytestmark = pytest.mark.asyncio(loop_scope="session")

_REGISTER_URL = "/auth/register"
_LOGIN_URL = "/auth/login"
_USER = {
    "email": "arcade_kid@example.com",
    "username": "arcadekid",
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "arcade_parent@example.com",
}


async def _login(client):
    await client.post(_REGISTER_URL, json=_USER)
    await client.post(_LOGIN_URL, json={"email": _USER["email"], "password": _USER["password"]})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_quiz_rush_session_then_score(client):
    # `client` is the existing authed-child fixture (mirror an existing child-auth API test)
    await _login(client)
    r = await client.get("/arcade/quiz-rush/session")
    assert r.status_code == 200
    items = r.json()["items"]
    # Score a submission that is correct for whatever items came back (may be empty in a bare test DB)
    answers = [{"lesson_id": it["lesson_id"], "choice_index": it["answer_index"], "time_ms": 800} for it in items]
    r2 = await client.post("/arcade/quiz-rush/score", json={"session_items": items, "answers": answers})
    assert r2.status_code == 200
    body = r2.json()
    assert body["points"] == len(items) * 10 + (len(items) * 5 if items else 0)
    assert body["coins_awarded"] >= 0
    assert "personal_best" in body and "leaderboard_rank" in body


async def test_leaderboard_endpoint(client):
    await _login(client)
    r = await client.get("/arcade/leaderboard?game=quiz_rush")
    assert r.status_code == 200
    assert isinstance(r.json()["entries"], list)


# ---------------------------------------------------------------------------
# MoneyWord endpoints
# ---------------------------------------------------------------------------

_MONEYWORD_TODAY_URL = "/arcade/moneyword/today"
_MONEYWORD_GUESS_URL = "/arcade/moneyword/guess"

_MW_USER = {
    "email": "mw_kid@example.com",
    "username": "mwkid",
    "password": "SecurePass123!",
    "dob": "2012-03-15",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "mw_parent@example.com",
}


async def _mw_login(client):
    await client.post(_REGISTER_URL, json=_MW_USER)
    await client.post(_LOGIN_URL, json={"email": _MW_USER["email"], "password": _MW_USER["password"]})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


def _seed_asset_word():
    return ArcadeWord(
        word="ASSET",
        definition="Something of value owned by a person or company.",
        language="en",
        length=5,
        status="approved",
        source="manual",
    )


async def test_moneyword_today_no_words(client):
    """503 when no approved words exist (fresh DB has none)."""
    await _mw_login(client)
    r = await client.get(_MONEYWORD_TODAY_URL)
    assert r.status_code == 503
    assert r.json()["detail"] == "no_daily_word"


async def test_moneyword_today_with_seed(client, db_session):
    """200 with correct shape when an approved ArcadeWord is in the DB."""
    db_session.add(_seed_asset_word())
    await db_session.flush()

    await _mw_login(client)
    r = await client.get(_MONEYWORD_TODAY_URL)
    assert r.status_code == 200
    body = r.json()
    assert body["length"] == 5
    assert body["completed"] is False
    assert body["solved"] is False
    assert body["definition"] is None
    assert body["guesses"] == []
    assert body["already_played"] is False


async def test_moneyword_guess_correct(client, db_session):
    """Correct guess → solved=True, completed=True, definition present."""
    db_session.add(_seed_asset_word())
    await db_session.flush()

    await _mw_login(client)
    r = await client.post(_MONEYWORD_GUESS_URL, json={"guess": "ASSET"})
    assert r.status_code == 200
    body = r.json()
    assert body["solved"] is True
    assert body["completed"] is True
    assert body["definition"] is not None
    assert len(body["guesses"]) == 1
    assert body["guesses"][0]["word"] == "ASSET"
    assert "correct" in body["guesses"][0]["feedback"]


async def test_moneyword_guess_second_attempt_409(client, db_session):
    """A second guess after the puzzle is completed → 409."""
    db_session.add(_seed_asset_word())
    await db_session.flush()

    await _mw_login(client)
    # First guess solves it.
    r = await client.post(_MONEYWORD_GUESS_URL, json={"guess": "ASSET"})
    assert r.status_code == 200
    # Second guess should be rejected.
    r2 = await client.post(_MONEYWORD_GUESS_URL, json={"guess": "ASSET"})
    assert r2.status_code == 409


async def test_moneyword_guess_wrong_length_422(client, db_session):
    """A guess of the wrong length → 422."""
    db_session.add(_seed_asset_word())
    await db_session.flush()

    # Fresh db_session per test — no prior plays, so no 409 risk.
    await _mw_login(client)

    r = await client.post(_MONEYWORD_GUESS_URL, json={"guess": "TOOLONG"})
    assert r.status_code == 422
