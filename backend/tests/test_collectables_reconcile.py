# backend/tests/test_collectables_reconcile.py
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from app.models.user import User, UserProgress
from app.models.cosmetics import CosmeticItem, UserCosmetic
from tests.test_content import _register_and_login
pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_reconcile_grants_eligible(client, db_session, monkeypatch):
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    await _register_and_login(client, email="rec@example.com", username="rec")
    u = await db_session.scalar(select(User).where(User.email == "rec@example.com"))
    p = await db_session.get(UserProgress, u.id) or UserProgress(user_id=u.id)
    p.streak_count = 10; db_session.add(p)
    now = datetime.now(UTC)
    db_session.add(CosmeticItem(slug="_rec_drop", name="R", emoji="👑", type="accessory", coin_cost=0,
                                is_premium=False, rarity="rare", unlock_type="streak_days", unlock_threshold=5,
                                available_from=now - timedelta(days=1), available_until=now + timedelta(days=1)))
    await db_session.commit()
    r = await client.post("/internal/collectables/reconcile", headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    item = await db_session.scalar(select(CosmeticItem).where(CosmeticItem.slug == "_rec_drop"))
    owned = await db_session.scalar(select(UserCosmetic).where(UserCosmetic.user_id == u.id, UserCosmetic.item_id == item.id))
    assert owned is not None
