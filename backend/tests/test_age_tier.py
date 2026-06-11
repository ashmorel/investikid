from datetime import date

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_age_tier_boundary():
    from app.services.age_tier import AGE_TIER_BOUNDARY, age_tier
    assert AGE_TIER_BOUNDARY == 14
    today = date(2026, 6, 6)
    assert age_tier(date(2016, 1, 1), today) == "explorer"   # age 10
    assert age_tier(date(2013, 1, 1), today) == "explorer"   # age 13
    assert age_tier(date(2012, 1, 1), today) == "investor"   # age 14
    assert age_tier(date(2009, 1, 1), today) == "investor"   # age 17
    assert age_tier(date(2012, 12, 31), today) == "explorer"  # still 13 on 2026-06-06


def test_user_age_tier_property():
    from app.models.user import User
    explorer = User(username="x", password_hash="x", dob=date(2015, 1, 1), country_code="GB", currency_code="GBP")
    investor = User(username="y", password_hash="x", dob=date(2010, 1, 1), country_code="GB", currency_code="GBP")
    assert explorer.age_tier == "explorer"
    assert investor.age_tier == "investor"


async def test_me_exposes_age_tier_for_investor(client, db_session):
    await client.post("/auth/register", json={
        "email": "teen@example.com", "username": "teen", "password": "SecurePass123!",
        "dob": "2011-01-01", "country_code": "GB", "currency_code": "GBP",
    })
    r = await client.get("/users/me")
    assert r.status_code == 200
    assert r.json()["age_tier"] == "investor"


def test_age_register_directive_has_both_tiers():
    from app.services.age_tier import AGE_REGISTER_DIRECTIVE
    assert "10-13" in AGE_REGISTER_DIRECTIVE["explorer"]
    assert "14-18" in AGE_REGISTER_DIRECTIVE["investor"]
    assert AGE_REGISTER_DIRECTIVE["explorer"] != AGE_REGISTER_DIRECTIVE["investor"]


def test_home_greeting_prompt_includes_tier_directive():
    from app.services.age_tier import AGE_REGISTER_DIRECTIVE
    from app.services.home_greeting_service import _build_messages

    sys_e, _ = _build_messages(name="A", mode="start", lesson_label="L", streak_count=0, due_count=0, tier="explorer")
    sys_i, _ = _build_messages(name="A", mode="start", lesson_label="L", streak_count=0, due_count=0, tier="investor")
    assert AGE_REGISTER_DIRECTIVE["explorer"] in sys_e
    assert AGE_REGISTER_DIRECTIVE["investor"] in sys_i


def test_user_tier_override_precedence():
    from app.models.user import User
    kw = dict(username="x", password_hash="x", country_code="GB", currency_code="GBP")
    teen = User(dob=date(2010, 1, 1), **kw)  # ~16yo -> investor by dob
    teen.tier_override = "explorer"
    assert teen.age_tier == "explorer"
    teen.tier_override = None
    assert teen.age_tier == "investor"

    kid = User(dob=date(2015, 1, 1), **kw)  # ~11yo -> explorer by dob
    kid.tier_override = "investor"
    assert kid.age_tier == "investor"

    kid.tier_override = "wizard"  # junk stored value -> fall back to derived
    assert kid.age_tier == "explorer"
