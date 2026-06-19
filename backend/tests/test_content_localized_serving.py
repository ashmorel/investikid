import pytest
from sqlalchemy import select

from app.models.content import Lesson, Module
from app.models.content_translation import ContentTranslation
from app.models.user import User
from app.services.app_settings import set_enabled_content_languages

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_child(client, db_session, *, username):
    """Register + login a GB child, set CSRF, return the User."""
    payload = {
        "email": f"{username}@example.com",
        "username": username,
        "password": "SecurePass123!",
        "dob": "2012-06-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": f"{username}_parent@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return await db_session.scalar(select(User).where(User.username == username))


async def _create_gb_lesson(db_session):
    module = Module(
        topic="savings", title="GB i18n Mod", country_codes=[],
        is_premium=False, order_index=901, icon="💷", market_code="GB",
    )
    db_session.add(module)
    await db_session.flush()
    lesson = Lesson(
        module_id=module.id, type="card", xp_reward=0, order_index=0,
        content_json={"title": "Saving up", "body": "A plan for your money."},
    )
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(ContentTranslation(
        entity_type="lesson", entity_id=lesson.id, language="fr",
        translated_json={"title": "Faire des économies", "body": "Un plan pour ton argent."},
        source="auto", status="active", source_hash="x",
    ))
    await db_session.flush()
    return lesson


async def _set_language(db_session, user, language):
    user.language = language
    db_session.add(user)
    await db_session.flush()


async def test_fr_child_with_language_enabled_gets_french(client, db_session):
    lesson = await _create_gb_lesson(db_session)
    await set_enabled_content_languages(db_session, ["fr"])
    child = await _register_child(client, db_session, username="frkid")
    await _set_language(db_session, child, "fr")

    r = await client.get(f"/lessons/{lesson.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["content_json"]["title"] == "Faire des économies"
    assert body["content_json"]["body"] == "Un plan pour ton argent."
    assert body["machine_translated"] is True


async def test_en_child_gets_english(client, db_session):
    lesson = await _create_gb_lesson(db_session)
    await set_enabled_content_languages(db_session, ["fr"])
    child = await _register_child(client, db_session, username="enkid")
    # default language is "en"
    assert child.language == "en"

    r = await client.get(f"/lessons/{lesson.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["content_json"]["title"] == "Saving up"
    assert body["machine_translated"] is False


async def test_fr_child_with_language_disabled_gets_english(client, db_session):
    lesson = await _create_gb_lesson(db_session)
    # fr NOT enabled (kill-switch off)
    child = await _register_child(client, db_session, username="frkid2")
    await _set_language(db_session, child, "fr")

    r = await client.get(f"/lessons/{lesson.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["content_json"]["title"] == "Saving up"
    assert body["machine_translated"] is False
