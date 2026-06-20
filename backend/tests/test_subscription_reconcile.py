from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.subscription import Subscription
from app.models.user import User
from app.services import subscription_reconcile_service as recon

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed(db_session, *, parent, username, provider, external_id, status, period_end):
    child = User(username=username, password_hash="x", dob=date(2014, 1, 1),
                 country_code="GB", currency_code="GBP", parent_email=parent, is_premium=True)
    db_session.add(child)
    db_session.add(Subscription(
        parent_email=parent, provider=provider, external_id=external_id,
        stripe_subscription_id=external_id if provider == "stripe" else None,
        status=status, current_period_end=period_end,
    ))
    await db_session.flush()
    return child


async def test_reconcile_revokes_a_lapsed_stripe_row(db_session, monkeypatch):
    p = "recon-dead@example.com"
    child = await _seed(db_session, parent=p, username="recon-dead", provider="stripe",
                        external_id="sub_dead", status="active",
                        period_end=datetime.now(UTC) - timedelta(hours=1))
    monkeypatch.setattr(recon, "_repull_stripe",
                        lambda sub_id: ("canceled", datetime.now(UTC) - timedelta(hours=1)))
    summary = await recon.run(db_session)
    await db_session.commit()
    assert summary["updated"] >= 1
    assert child.is_premium is False


async def test_reconcile_keeps_an_autorenewed_row(db_session, monkeypatch):
    p = "recon-live@example.com"
    child = await _seed(db_session, parent=p, username="recon-live", provider="stripe",
                        external_id="sub_live", status="active",
                        period_end=datetime.now(UTC) - timedelta(hours=1))
    monkeypatch.setattr(recon, "_repull_stripe",
                        lambda sub_id: ("active", datetime.now(UTC) + timedelta(days=20)))
    await recon.run(db_session)
    await db_session.commit()
    assert child.is_premium is True


async def test_one_provider_error_does_not_abort_batch(db_session, monkeypatch):
    p = "recon-err@example.com"
    await _seed(db_session, parent=p, username="recon-err", provider="stripe",
                external_id="sub_err", status="active",
                period_end=datetime.now(UTC) - timedelta(hours=1))
    def boom(_):
        raise RuntimeError("provider down")
    monkeypatch.setattr(recon, "_repull_stripe", boom)
    summary = await recon.run(db_session)
    assert summary["errored"] >= 1
    assert "checked" in summary
