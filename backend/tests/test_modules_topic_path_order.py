import pytest
from sqlalchemy import select

from app.models.content import Module
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _register_and_login(client, email="learner@example.com", username="learner"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _seed_modules(db_session):
    m0 = Module(topic="budgeting", title="Budgeting", country_codes=[], is_premium=False, order_index=0)
    m1 = Module(topic="stocks", title="Stocks", country_codes=[], is_premium=False, order_index=1)
    m2 = Module(topic="savings", title="Savings", country_codes=[], is_premium=False, order_index=2)
    db_session.add_all([m0, m1, m2])
    await db_session.commit()
    return m0, m1, m2


async def test_modules_ordered_by_preferred_topic_first(client, db_session):
    await _seed_modules(db_session)
    await _register_and_login(client, email="prefuser@example.com", username="prefuser")

    # Set the user's topic_path to a seeded topic that is NOT first by order_index.
    user = await db_session.scalar(select(User).where(User.email == "prefuser@example.com"))
    user.topic_path = "savings"
    await db_session.commit()

    response = await client.get("/modules")
    assert response.status_code == 200
    titles = [m["title"] for m in response.json()]
    # Preferred topic's module first, remaining stay in order_index order.
    assert titles == ["Savings", "Budgeting", "Stocks"]


async def test_modules_default_order_when_no_topic_path(client, db_session):
    await _seed_modules(db_session)
    await _register_and_login(client, email="nopref@example.com", username="nopref")

    user = await db_session.scalar(select(User).where(User.email == "nopref@example.com"))
    assert user.topic_path is None

    response = await client.get("/modules")
    assert response.status_code == 200
    titles = [m["title"] for m in response.json()]
    assert titles == ["Budgeting", "Stocks", "Savings"]
