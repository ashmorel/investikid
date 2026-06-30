"""Parent mastery report (M6 Task 1 + Task 2 growth block)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.content import Level, LevelMastery, Module
from app.models.mastery import MasteryCheckpoint, MasteryCheckpointTopic
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


# ---------------------------------------------------------------------------
# Task 2 — growth block helpers
# ---------------------------------------------------------------------------


async def _make_checkpoint(
    db_session,
    child: User,
    *,
    kind: str,
    overall_score: float | None = None,
    session_count: int = 0,
    taken_at: datetime | None = None,
    topics: list[tuple[str, int, int]] | None = None,
) -> MasteryCheckpoint:
    """Create a MasteryCheckpoint with optional topic rows for *child*."""
    cp = MasteryCheckpoint(
        user_id=child.id,
        market_code="GB",
        kind=kind,
        overall_score=overall_score,
        session_count=session_count,
        taken_at=taken_at or datetime.now(UTC),
    )
    db_session.add(cp)
    await db_session.flush()
    for topic, correct, attempted in (topics or []):
        db_session.add(
            MasteryCheckpointTopic(
                checkpoint_id=cp.id,
                topic=topic,
                correct=correct,
                attempted=attempted,
            )
        )
    await db_session.flush()
    return cp


# ---------------------------------------------------------------------------
# Task 2 — growth block: child with baseline + progress → correct growth
# ---------------------------------------------------------------------------


async def test_growth_block_with_baseline_and_progress(db_session):
    """Entry growth has has_baseline=True with correct deltas and focus_topic."""
    parent = f"grw1_{uuid.uuid4().hex[:6]}@x.test"
    child, *_ = await _seed(db_session, parent, objectives=["save money"])

    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    prog_time = base_time + timedelta(days=30)

    await _make_checkpoint(
        db_session, child,
        kind="baseline",
        overall_score=0.4,
        session_count=5,
        taken_at=base_time,
        topics=[("budgeting", 2, 5), ("savings", 1, 5)],
    )
    await _make_checkpoint(
        db_session, child,
        kind="progress",
        overall_score=0.8,
        session_count=10,
        taken_at=prog_time,
        # savings is 2/5=0.4 (lower than budgeting 4/5=0.8) → focus_topic=savings
        topics=[("budgeting", 4, 5), ("savings", 2, 5)],
    )

    report = await build_mastery_report(db_session, parent, days=30)
    entry = next(c for c in report["children"] if c["user_id"] == str(child.id))

    growth = entry["growth"]
    assert growth is not None
    assert growth["has_baseline"] is True
    assert growth["baseline_overall"] == pytest.approx(0.4)
    assert growth["latest_overall"] == pytest.approx(0.8)
    assert growth["overall_delta"] == pytest.approx(0.4)

    topic_deltas = {d["topic"]: d for d in growth["topic_deltas"]}
    assert "budgeting" in topic_deltas
    assert topic_deltas["budgeting"]["baseline_score"] == pytest.approx(2 / 5)
    assert topic_deltas["budgeting"]["latest_score"] == pytest.approx(4 / 5)
    assert topic_deltas["budgeting"]["delta"] == pytest.approx(4 / 5 - 2 / 5)

    assert "savings" in topic_deltas

    # focus_topic = lowest latest score = savings (2/5=0.4 < budgeting 4/5=0.8)
    assert growth["focus_topic"] == "savings"


# ---------------------------------------------------------------------------
# Task 2 — growth block: child with no baseline → growth.has_baseline=False
# ---------------------------------------------------------------------------


async def test_growth_block_no_baseline(db_session):
    """A child with no checkpoints → growth.has_baseline=False, nulls, empty topic_deltas."""
    parent = f"grw2_{uuid.uuid4().hex[:6]}@x.test"
    child, *_ = await _seed(db_session, parent, objectives=["learn investing"])

    report = await build_mastery_report(db_session, parent, days=30)
    entry = next(c for c in report["children"] if c["user_id"] == str(child.id))

    growth = entry["growth"]
    assert growth is not None
    assert growth["has_baseline"] is False
    assert growth["overall_delta"] is None
    assert growth["baseline_overall"] is None
    assert growth["latest_overall"] is None
    assert growth["topic_deltas"] == []
    assert growth["focus_topic"] is None


# ---------------------------------------------------------------------------
# Task 2 — existing fields unchanged (regression)
# ---------------------------------------------------------------------------


async def test_growth_block_does_not_break_existing_fields(db_session):
    """Adding growth must leave all pre-existing entry fields intact."""
    parent = f"grw3_{uuid.uuid4().hex[:6]}@x.test"
    child, *_ = await _seed(
        db_session, parent,
        objectives=["understand risk"],
        standards=[{"framework": "MaPS", "code": "MM-2"}],
    )

    report = await build_mastery_report(db_session, parent, days=30)
    entry = next(c for c in report["children"] if c["user_id"] == str(child.id))

    # All pre-existing fields still present
    assert "mastered_count" in entry
    assert "mastered_total" in entry
    assert "objectives" in entry
    assert "standards" in entry
    assert "weak_topic" in entry
    assert "next_recommendation" in entry
    # And growth is present (may be None or dict)
    assert "growth" in entry


# ---------------------------------------------------------------------------
# Task 2 — two children of same parent each get their OWN growth
# ---------------------------------------------------------------------------


async def test_growth_block_per_child_scoping(db_session):
    """Two children of the same parent get independent growth blocks."""
    parent = f"grw4_{uuid.uuid4().hex[:6]}@x.test"

    child_a, *_ = await _seed(db_session, parent, objectives=["budgeting basics"])
    child_b, *_ = await _seed(db_session, parent, objectives=["savings habits"])

    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    prog_time = base_time + timedelta(days=20)

    # Only child_a gets checkpoints
    await _make_checkpoint(
        db_session, child_a,
        kind="baseline",
        overall_score=0.5,
        session_count=3,
        taken_at=base_time,
        topics=[("budgeting", 2, 4)],
    )
    await _make_checkpoint(
        db_session, child_a,
        kind="progress",
        overall_score=0.75,
        session_count=6,
        taken_at=prog_time,
        topics=[("budgeting", 3, 4)],
    )

    report = await build_mastery_report(db_session, parent, days=30)
    children_map = {c["user_id"]: c for c in report["children"]}

    entry_a = children_map[str(child_a.id)]
    entry_b = children_map[str(child_b.id)]

    # child_a has baseline data
    assert entry_a["growth"]["has_baseline"] is True
    assert entry_a["growth"]["overall_delta"] == pytest.approx(0.25)

    # child_b has no checkpoints → no baseline
    assert entry_b["growth"]["has_baseline"] is False
    assert entry_b["growth"]["topic_deltas"] == []


# ---------------------------------------------------------------------------
# Task 2 — different parent's child is not included
# ---------------------------------------------------------------------------


async def test_growth_block_excludes_other_parents_children(db_session):
    """A child belonging to a different parent is not visible in the report."""
    parent_a = f"grw5a_{uuid.uuid4().hex[:6]}@x.test"
    parent_b = f"grw5b_{uuid.uuid4().hex[:6]}@x.test"

    child_a, *_ = await _seed(db_session, parent_a, objectives=["invest wisely"])
    child_b, *_ = await _seed(db_session, parent_b, objectives=["save more"])

    report = await build_mastery_report(db_session, parent_a, days=30)
    ids_in_report = {c["user_id"] for c in report["children"]}

    assert str(child_a.id) in ids_in_report
    assert str(child_b.id) not in ids_in_report
