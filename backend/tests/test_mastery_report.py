"""Parent mastery report (M6 Task 1)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.content import Level, LevelMastery, Module
from app.models.user import User
from app.services.mastery_report_service import build_mastery_report
from tests.test_billing import _setup_parent

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _child(parent_email: str) -> User:
    suffix = uuid.uuid4().hex[:8]
    return User(
        username=f"mr{suffix}",
        email=f"mr{suffix}@x.test",
        password_hash="x",
        dob=datetime(2014, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
        parent_email=parent_email,
    )


def _module(title="Saving Basics", standards=None):
    return Module(
        topic="saving", title=title, country_codes=["GB"], order_index=0,
        standards_alignment=standards,
    )


def _level(module, title="Level 1", objectives=None):
    return Level(module_id=module.id, title=title, order_index=0, learning_objectives=objectives)


async def _seed(db_session, parent_email, *, objectives, standards=None, mastered_days_ago=2):
    child = _child(parent_email)
    module = _module(standards=standards)
    db_session.add_all([child, module])
    await db_session.flush()
    level = _level(module, objectives=objectives)
    db_session.add(level)
    await db_session.flush()
    db_session.add(LevelMastery(
        user_id=child.id, level_id=level.id,
        mastered_at=datetime.now(UTC) - timedelta(days=mastered_days_ago), score=0.9,
    ))
    await db_session.commit()
    return child, module, level


async def test_report_counts_window_masteries_and_objectives(db_session):
    parent = f"mrp{uuid.uuid4().hex[:6]}@x.test"
    child, *_ = await _seed(
        db_session, parent,
        objectives=["explain what a stock is", "explain what a stock is", "spot a scam"],
        standards=[{"framework": "MaPS", "code": "MM-1"}],
    )
    report = await build_mastery_report(db_session, parent, days=30)
    assert report["window_days"] == 30
    assert report["household_mastered_count"] == 1
    entry = next(c for c in report["children"] if c["user_id"] == str(child.id))
    assert entry["mastered_count"] == 1
    assert entry["mastered_total"] == 1
    # deduped
    assert entry["objectives"] == ["explain what a stock is", "spot a scam"]
    assert entry["standards"] == [{"framework": "MaPS", "code": "MM-1"}]


async def test_report_excludes_out_of_window_but_counts_total(db_session):
    parent = f"mrq{uuid.uuid4().hex[:6]}@x.test"
    child, *_ = await _seed(db_session, parent, objectives=["old skill"], mastered_days_ago=60)
    report = await build_mastery_report(db_session, parent, days=30)
    entry = next(c for c in report["children"] if c["user_id"] == str(child.id))
    assert entry["mastered_count"] == 0
    assert entry["mastered_total"] == 1
    assert entry["objectives"] == []


async def test_report_caps_objectives_at_eight(db_session):
    parent = f"mrr{uuid.uuid4().hex[:6]}@x.test"
    await _seed(db_session, parent, objectives=[f"skill {i}" for i in range(12)])
    report = await build_mastery_report(db_session, parent, days=30)
    assert len(report["children"][0]["objectives"]) == 8


async def test_report_empty_household(db_session):
    report = await build_mastery_report(db_session, f"none{uuid.uuid4().hex[:6]}@x.test", days=30)
    assert report["children"] == []
    assert report["household_mastered_count"] == 0


async def test_endpoint_requires_parent_auth(client):
    assert (await client.get("/parent/mastery-report")).status_code == 401


async def test_endpoint_returns_report(client, db_session):
    parent = f"mre{uuid.uuid4().hex[:6]}@example.com"
    await _setup_parent(
        client, db_session, parent_email=parent,
        child_email=f"mrek{uuid.uuid4().hex[:6]}@example.com",
        child_username=f"mrek{uuid.uuid4().hex[:6]}",
    )
    r = await client.get("/parent/mastery-report")
    assert r.status_code == 200
    body = r.json()
    assert body["window_days"] == 30
    assert isinstance(body["children"], list)
    assert len(body["children"]) == 1
    assert body["children"][0]["mastered_count"] == 0
