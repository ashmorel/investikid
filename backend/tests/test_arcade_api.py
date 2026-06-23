import pytest

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
