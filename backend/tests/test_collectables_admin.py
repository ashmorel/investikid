# backend/tests/test_collectables_admin.py
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import User
from app.services import collectables_admin_service as svc
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_unscheduled_pool_item_hidden_from_shop(client, db_session):
    # A drop-eligible pool item with no unlock_type must NOT appear in the buyable shop.
    db_session.add(CosmeticItem(
        slug="_pool_hat", name="Pool Hat", emoji="🎩", type="accessory",
        coin_cost=0, is_premium=False, drop_eligible=True, unlock_type=None,
    ))
    await db_session.commit()
    await _register_and_login(client, email="shopper@example.com", username="shopper")
    r = await client.get("/cosmetics")
    assert r.status_code == 200
    slugs = {i["slug"] for i in r.json()["items"]}
    assert "_pool_hat" not in slugs


def _pool_item(slug="_pool_a"):
    return CosmeticItem(slug=slug, name="A", emoji="🎩", type="accessory",
                        coin_cost=0, is_premium=False, drop_eligible=True)


async def test_schedule_then_listed_as_scheduled(db_session):
    item = _pool_item("_sched_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now + timedelta(days=1),
        available_until=now + timedelta(days=8),
    )
    pool = await svc.list_pool(db_session)
    assert item.id not in {p.id for p in pool}  # left the pool
    drops = await svc.list_drops(db_session, now)
    row = next(d for d in drops if d.item.id == item.id)
    assert row.status == "scheduled"
    assert row.owned_count == 0


async def test_schedule_rejects_invalid(db_session):
    item = _pool_item("_sched_bad")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    for kwargs, code in [
        (dict(unlock_type="nope"), "bad_unlock_type"),
        (dict(rarity="ultra"), "bad_rarity"),
        (dict(unlock_threshold=0), "bad_threshold"),
        (dict(available_until=now), "bad_window"),  # until <= from
    ]:
        base = dict(item_id=item.id, rarity="rare", unlock_type="streak_days",
                    unlock_threshold=5, available_from=now + timedelta(days=1),
                    available_until=now + timedelta(days=8))
        base.update(kwargs)
        with pytest.raises(svc.AdminError) as ei:
            await svc.schedule_drop(db_session, **base)
        assert ei.value.code == code


async def test_live_drop_only_enddate_editable(db_session):
    item = _pool_item("_live_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    # already live: from in the past, until in the future
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now - timedelta(days=1),
        available_until=now + timedelta(days=7),
    )
    # changing the rule on a live drop is rejected
    with pytest.raises(svc.AdminError) as ei:
        await svc.edit_drop(db_session, item_id=item.id, now=now, unlock_threshold=99)
    assert ei.value.code == "live_locked"
    # ending early IS allowed
    new_end = now + timedelta(hours=1)
    await svc.edit_drop(db_session, item_id=item.id, now=now, available_until=new_end)
    refreshed = await db_session.get(CosmeticItem, item.id)
    assert refreshed.available_until == new_end


async def test_unschedule_blocked_when_owned(db_session):
    item = _pool_item("_owned_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now + timedelta(days=1),
        available_until=now + timedelta(days=8),
    )
    # a child owns it
    u = User(email="o@e.com", username="owno", password_hash="x",
             dob=date(2012, 1, 1), country_code="GB", currency_code="USD")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserCosmetic(user_id=u.id, item_id=item.id))
    await db_session.flush()
    with pytest.raises(svc.AdminError) as ei:
        await svc.unschedule_drop(db_session, item_id=item.id, now=now)
    assert ei.value.code == "owned_cannot_unschedule"


async def test_unschedule_clears_fields_when_clean(db_session):
    item = _pool_item("_clean_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now + timedelta(days=1),
        available_until=now + timedelta(days=8),
    )
    await svc.unschedule_drop(db_session, item_id=item.id, now=now)
    refreshed = await db_session.get(CosmeticItem, item.id)
    assert refreshed.unlock_type is None
    assert refreshed.rarity is None
    assert refreshed.available_from is None
    assert refreshed.drop_eligible is True  # still a pool item


async def test_unschedule_on_live_raises_not_scheduled(db_session):
    item = _pool_item("_live_unsch_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    # schedule a drop that is already live (from in the past, until in the future)
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now - timedelta(days=1),
        available_until=now + timedelta(days=7),
    )
    # attempt to unschedule a live drop with zero owners should raise "not_scheduled"
    with pytest.raises(svc.AdminError) as ei:
        await svc.unschedule_drop(db_session, item_id=item.id, now=now)
    assert ei.value.code == "not_scheduled"


async def test_live_edit_rejects_past_end_date(db_session):
    item = _pool_item("_live_past_end_a")
    db_session.add(item)
    await db_session.flush()
    now = datetime.now(UTC)
    # schedule a drop that is already live (from in the past, until in the future)
    await svc.schedule_drop(
        db_session, item_id=item.id, rarity="rare", unlock_type="streak_days",
        unlock_threshold=5, available_from=now - timedelta(days=1),
        available_until=now + timedelta(days=7),
    )
    # attempt to edit with a past end-date should raise "bad_window"
    past_end = now - timedelta(hours=1)
    with pytest.raises(svc.AdminError) as ei:
        await svc.edit_drop(db_session, item_id=item.id, now=now, available_until=past_end)
    assert ei.value.code == "bad_window"
