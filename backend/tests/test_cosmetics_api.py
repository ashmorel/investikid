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


async def _own_item(db_session, user, item: CosmeticItem) -> UserCosmetic:
    """Give the user ownership of a CosmeticItem (without equipped)."""
    from datetime import UTC, datetime

    uc = UserCosmetic(user_id=user.id, item_id=item.id, unlocked_at=datetime.now(UTC))
    db_session.add(uc)
    await db_session.flush()
    return uc


async def _seed_typed_items(db_session):
    """Ensure two typed items exist: one accessory, one background."""
    from app.models.cosmetics import CosmeticItem as CI

    acc = await db_session.scalar(select(CI).where(CI.slug == "_test_acc"))
    if acc is None:
        acc = CI(slug="_test_acc", name="Test Acc", emoji="🎀", type="accessory",
                 coin_cost=0, is_premium=False)
        db_session.add(acc)

    bg = await db_session.scalar(select(CI).where(CI.slug == "_test_bg"))
    if bg is None:
        bg = CI(slug="_test_bg", name="Test BG", emoji="🖼️", type="background",
                coin_cost=0, is_premium=False)
        db_session.add(bg)

    acc2 = await db_session.scalar(select(CI).where(CI.slug == "_test_bg2"))
    if acc2 is None:
        acc2 = CI(slug="_test_bg2", name="Test BG2", emoji="🌅", type="background",
                  coin_cost=0, is_premium=False)
        db_session.add(acc2)

    await db_session.flush()
    return (
        await db_session.scalar(select(CI).where(CI.slug == "_test_acc")),
        await db_session.scalar(select(CI).where(CI.slug == "_test_bg")),
        await db_session.scalar(select(CI).where(CI.slug == "_test_bg2")),
    )


async def test_equip_is_per_category(client, db_session):
    """Equipping an accessory then a background leaves BOTH equipped."""
    user = await _login_with_coins(client, db_session, coins=0)
    acc_item, bg_item, _ = await _seed_typed_items(db_session)

    await _own_item(db_session, user, acc_item)
    await _own_item(db_session, user, bg_item)
    await db_session.commit()

    assert (await client.post(f"/cosmetics/{acc_item.id}/equip")).status_code == 200
    assert (await client.post(f"/cosmetics/{bg_item.id}/equip")).status_code == 200

    rows = (
        await db_session.execute(
            select(UserCosmetic).where(UserCosmetic.user_id == user.id)
        )
    ).scalars().all()
    equipped_ids = {r.item_id for r in rows if r.equipped}
    assert acc_item.id in equipped_ids, "accessory should still be equipped"
    assert bg_item.id in equipped_ids, "background should also be equipped"


async def test_equip_swaps_within_category(client, db_session):
    """Equipping a second background replaces only the first background."""
    user = await _login_with_coins(client, db_session, coins=0)
    _, bg1, bg2 = await _seed_typed_items(db_session)

    await _own_item(db_session, user, bg1)
    await _own_item(db_session, user, bg2)
    await db_session.commit()

    assert (await client.post(f"/cosmetics/{bg1.id}/equip")).status_code == 200
    assert (await client.post(f"/cosmetics/{bg2.id}/equip")).status_code == 200

    rows = (
        await db_session.execute(
            select(UserCosmetic).where(UserCosmetic.user_id == user.id)
        )
    ).scalars().all()
    equipped_ids = {r.item_id for r in rows if r.equipped}
    assert bg2.id in equipped_ids, "second background should be equipped"
    assert bg1.id not in equipped_ids, "first background should be unequipped"


async def test_unequip_item_only_clears_that_item(client, db_session):
    """POST /cosmetics/{id}/unequip unequips just that item; others stay equipped."""
    user = await _login_with_coins(client, db_session, coins=0)
    acc_item, bg_item, _ = await _seed_typed_items(db_session)

    uc_acc = await _own_item(db_session, user, acc_item)
    uc_bg = await _own_item(db_session, user, bg_item)
    uc_acc.equipped = True
    uc_bg.equipped = True
    await db_session.commit()

    r = await client.post(f"/cosmetics/{bg_item.id}/unequip")
    assert r.status_code == 200

    await db_session.refresh(uc_acc)
    await db_session.refresh(uc_bg)
    assert uc_acc.equipped is True, "accessory should still be equipped"
    assert uc_bg.equipped is False, "background should be unequipped"


async def test_shop_item_exposes_type(client, db_session):
    """GET /cosmetics returns `type` on every item."""
    await _login_with_coins(client, db_session, coins=0)
    r = await client.get("/cosmetics")
    assert r.status_code == 200
    assert all("type" in it for it in r.json()["items"])


async def test_accessories_stack(client, db_session):
    """Accessories STACK: equipping a second accessory leaves both equipped;
    per-item unequip removes just one."""
    user = await _login_with_coins(client, db_session, coins=500)
    hat = await _item(db_session, "party_hat")
    bow = await _item(db_session, "bow")
    assert (await client.post(f"/cosmetics/{hat.id}/buy")).status_code == 200
    assert (await client.post(f"/cosmetics/{bow.id}/buy")).status_code == 200

    assert (await client.post(f"/cosmetics/{hat.id}/equip")).status_code == 200
    assert (await client.post(f"/cosmetics/{bow.id}/equip")).status_code == 200

    async def _equipped_ids():
        rows = (
            await db_session.execute(
                select(UserCosmetic).where(UserCosmetic.user_id == user.id)
            )
        ).scalars().all()
        for r in rows:
            await db_session.refresh(r)
        return {r.item_id for r in rows if r.equipped}

    equipped = await _equipped_ids()
    assert hat.id in equipped and bow.id in equipped, "both accessories stay equipped"

    # Take off just the hat -> bow remains.
    assert (await client.post(f"/cosmetics/{hat.id}/unequip")).status_code == 200
    equipped = await _equipped_ids()
    assert hat.id not in equipped and bow.id in equipped

    # equipping an unowned item -> 404
    crown = await _item(db_session, "crown")
    assert (await client.post(f"/cosmetics/{crown.id}/equip")).status_code == 404


async def test_accessories_swap_within_slot(client, db_session):
    """Same-slot accessories are mutually exclusive (one hat at a time), but
    different slots stack (a hat + eyewear can be worn together)."""
    user = await _login_with_coins(client, db_session, coins=2000, premium=True)
    party_hat = await _item(db_session, "party_hat")   # head slot
    top_hat = await _item(db_session, "top_hat")        # head slot
    sunglasses = await _item(db_session, "sunglasses")  # eyes slot
    for it in (party_hat, top_hat, sunglasses):
        assert (await client.post(f"/cosmetics/{it.id}/buy")).status_code == 200

    async def _equipped_ids():
        rows = (
            await db_session.execute(
                select(UserCosmetic).where(UserCosmetic.user_id == user.id)
            )
        ).scalars().all()
        for r in rows:
            await db_session.refresh(r)
        return {r.item_id for r in rows if r.equipped}

    # Equip a hat, then sunglasses -> different slots, both stay on.
    assert (await client.post(f"/cosmetics/{party_hat.id}/equip")).status_code == 200
    assert (await client.post(f"/cosmetics/{sunglasses.id}/equip")).status_code == 200
    equipped = await _equipped_ids()
    assert party_hat.id in equipped and sunglasses.id in equipped

    # Equip a second hat -> swaps out the first hat, leaves sunglasses on.
    assert (await client.post(f"/cosmetics/{top_hat.id}/equip")).status_code == 200
    equipped = await _equipped_ids()
    assert top_hat.id in equipped, "new hat equipped"
    assert party_hat.id not in equipped, "old hat swapped out (one hat at a time)"
    assert sunglasses.id in equipped, "different-slot accessory unaffected"
