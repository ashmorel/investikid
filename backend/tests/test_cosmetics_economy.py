"""Learning coins + cosmetics seed (M8 Task 1)."""
from datetime import date

import pytest
from sqlalchemy import select

from app.models.cosmetics import CosmeticItem
from app.models.user import UserProgress
from app.seed.cosmetics import CATALOG, seed_cosmetics
from app.services.xp_service import record_xp

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_record_xp_grants_coins_one_to_one():
    p = UserProgress(xp=100, level=2, virtual_coins=40, daily_goal_xp=30, xp_today=0)
    record_xp(p, 25, today=date(2026, 6, 12))
    assert p.virtual_coins == 65
    assert p.xp == 125


async def test_seed_cosmetics_idempotent(db_session):
    n1 = await seed_cosmetics(db_session)
    n2 = await seed_cosmetics(db_session)
    assert n1 == n2 == len(CATALOG)
    rows = (await db_session.scalars(select(CosmeticItem))).all()
    slugs = {r.slug for r in rows}
    assert {"party_hat", "monocle", "top_hat"} <= slugs
    assert len([r for r in rows if r.slug in {c["slug"] for c in CATALOG}]) == len(CATALOG)
    monocle = next(r for r in rows if r.slug == "monocle")
    assert monocle.is_premium is True and monocle.coin_cost == 200


async def test_progress_payload_includes_coins(client, db_session):
    import uuid

    from tests.test_content import _register_and_login

    suffix = uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"c{suffix}@example.com", username=f"c{suffix}")
    r = await client.get("/users/me/progress")
    assert r.status_code == 200
    assert r.json()["virtual_coins"] == 0
