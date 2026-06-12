"""Penny's Shop API (M8 Task 2)."""
import uuid

import pytest
from sqlalchemy import select

from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import User, UserProgress
from app.seed.cosmetics import seed_cosmetics
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _login_with_coins(client, db_session, *, coins=1000, premium=False):
    await seed_cosmetics(db_session)
    await db_session.commit()
    suffix = uuid.uuid4().hex[:8]
    email = f"shop{suffix}@example.com"
    await _register_and_login(client, email=email, username=f"shop{suffix}")
    user = await db_session.scalar(select(User).where(User.email == email))
    user.is_premium = premium
    progress = await db_session.get(UserProgress, user.id)
    if progress is None:
        progress = UserProgress(user_id=user.id)
        db_session.add(progress)
    progress.virtual_coins = coins
    await db_session.commit()
    return user


async def _item(db_session, slug) -> CosmeticItem:
    return await db_session.scalar(select(CosmeticItem).where(CosmeticItem.slug == slug))


async def test_shop_requires_auth(client):
    assert (await client.get("/cosmetics")).status_code == 401


async def test_shop_state_and_can_buy(client, db_session):
    await _login_with_coins(client, db_session, coins=80, premium=False)
    r = await client.get("/cosmetics")
    assert r.status_code == 200
    body = r.json()
    assert body["coins"] == 80
    by_slug = {i["slug"]: i for i in body["items"]}
    assert by_slug["party_hat"]["can_buy"] is True       # 50 <= 80
    assert by_slug["headphones"]["can_buy"] is False     # 100 > 80
    assert by_slug["monocle"]["can_buy"] is False        # premium-gated
    assert by_slug["monocle"]["is_premium"] is True


async def test_buy_deducts_and_owns(client, db_session):
    await _login_with_coins(client, db_session, coins=200)
    item = await _item(db_session, "party_hat")
    r = await client.post(f"/cosmetics/{item.id}/buy")
    assert r.status_code == 200
    assert r.json()["coins"] == 150
    # duplicate buy -> 409
    assert (await client.post(f"/cosmetics/{item.id}/buy")).status_code == 409


async def test_buy_guards(client, db_session):
    user = await _login_with_coins(client, db_session, coins=10, premium=False)
    cheap = await _item(db_session, "party_hat")
    assert (await client.post(f"/cosmetics/{cheap.id}/buy")).status_code == 400
    premium_item = await _item(db_session, "monocle")
    assert (await client.post(f"/cosmetics/{premium_item.id}/buy")).status_code == 403
    assert (await client.post(f"/cosmetics/{uuid.uuid4()}/buy")).status_code == 404
    assert user is not None


async def test_equip_is_exclusive(client, db_session):
    user = await _login_with_coins(client, db_session, coins=500)
    hat = await _item(db_session, "party_hat")
    bow = await _item(db_session, "bow")
    assert (await client.post(f"/cosmetics/{hat.id}/buy")).status_code == 200
    assert (await client.post(f"/cosmetics/{bow.id}/buy")).status_code == 200

    assert (await client.post(f"/cosmetics/{hat.id}/equip")).status_code == 200
    assert (await client.post(f"/cosmetics/{bow.id}/equip")).status_code == 200

    rows = (
        await db_session.execute(
            select(UserCosmetic).where(UserCosmetic.user_id == user.id)
        )
    ).scalars().all()
    equipped = [r for r in rows if r.equipped]
    assert len(equipped) == 1 and equipped[0].item_id == bow.id

    assert (await client.post("/cosmetics/unequip")).status_code == 200
    await db_session.refresh(equipped[0])
    assert equipped[0].equipped is False

    # equipping an unowned item -> 404
    crown = await _item(db_session, "crown")
    assert (await client.post(f"/cosmetics/{crown.id}/equip")).status_code == 404
