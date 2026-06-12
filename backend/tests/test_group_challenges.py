"""Co-op group challenge engine (M9 Task 1)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.gamification import Challenge, GroupChallengeCompletion, UserChallenge
from app.models.group import GroupMembership, LeaderboardGroup
from app.models.user import User, UserProgress
from app.services.gamification_service import update_challenge_progress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _child(db_session, coins=0) -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"gc{suffix}", email=f"gc{suffix}@example.com", password_hash="x",
        dob=datetime(2014, 1, 1).date(), country_code="GB", currency_code="GBP",
        parent_email="p@example.com",
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProgress(user_id=user.id, xp=0, level=1, virtual_coins=coins))
    return user


async def _group(db_session, *members) -> LeaderboardGroup:
    group = LeaderboardGroup(
        name="Test Group", code=f"G{uuid.uuid4().hex[:7].upper()}",
        owner_parent_email="p@example.com",
    )
    db_session.add(group)
    await db_session.flush()
    for m in members:
        db_session.add(GroupMembership(group_id=group.id, user_id=m.id, added_by_parent_email="p@example.com"))
    await db_session.flush()
    return group


def _challenge(*, scope="group", target=5, xp=50, ctype="lessons_completed") -> Challenge:
    now = datetime.now(UTC)
    return Challenge(
        title="Group goal", description="Together!", type=ctype,
        target_value=target, xp_reward=xp,
        starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=6),
        scope=scope,
    )


async def test_group_progress_sums_and_rewards_every_member_once(db_session):
    a, b = await _child(db_session), await _child(db_session)
    group = await _group(db_session, a, b)
    ch = _challenge(target=5, xp=50)
    db_session.add(ch)
    await db_session.flush()

    await update_challenge_progress(db_session, a.id, "lessons_completed", increment=3)
    # group total 3 < 5: nobody completed
    rows = (await db_session.scalars(select(UserChallenge).where(UserChallenge.challenge_id == ch.id))).all()
    assert all(r.completed_at is None for r in rows)

    await update_challenge_progress(db_session, b.id, "lessons_completed", increment=2)
    # group total 5 >= 5: completion row + both members rewarded
    completion = await db_session.scalar(
        select(GroupChallengeCompletion).where(
            GroupChallengeCompletion.group_id == group.id,
            GroupChallengeCompletion.challenge_id == ch.id,
        )
    )
    assert completion is not None
    rows = (await db_session.scalars(select(UserChallenge).where(UserChallenge.challenge_id == ch.id))).all()
    assert len(rows) == 2 and all(r.completed_at is not None for r in rows)
    pa = await db_session.get(UserProgress, a.id)
    pb = await db_session.get(UserProgress, b.id)
    assert pa.xp == 50 and pb.xp == 50

    # further progress must NOT double-reward
    await update_challenge_progress(db_session, a.id, "lessons_completed", increment=3)
    pa = await db_session.get(UserProgress, a.id)
    assert pa.xp == 50


async def test_personal_challenges_unchanged(db_session):
    a = await _child(db_session)
    ch = _challenge(scope="personal", target=2, xp=30)
    db_session.add(ch)
    await db_session.flush()

    completed = await update_challenge_progress(db_session, a.id, "lessons_completed", increment=2)
    assert any(c.id == ch.id for c in completed)
    uc = await db_session.get(UserChallenge, (a.id, ch.id))
    assert uc.completed_at is not None
    # personal completion does NOT award via the engine (existing behaviour: caller handles)
    pa = await db_session.get(UserProgress, a.id)
    assert pa.xp == 0


async def test_member_without_progress_row_still_rewarded(db_session):
    a, b = await _child(db_session), await _child(db_session)
    await _group(db_session, a, b)
    ch = _challenge(target=3, xp=20)
    db_session.add(ch)
    await db_session.flush()

    # only A contributes; B never triggered the event type
    await update_challenge_progress(db_session, a.id, "lessons_completed", increment=3)
    pb = await db_session.get(UserProgress, b.id)
    assert pb.xp == 20  # rewarded as part of the group
    ucb = await db_session.get(UserChallenge, (b.id, ch.id))
    assert ucb is not None and ucb.completed_at is not None


async def test_child_in_two_groups_counts_in_both(db_session):
    a, b, c = await _child(db_session), await _child(db_session), await _child(db_session)
    g1 = await _group(db_session, a, b)
    g2 = await _group(db_session, a, c)
    ch = _challenge(target=2, xp=10)
    db_session.add(ch)
    await db_session.flush()

    await update_challenge_progress(db_session, a.id, "lessons_completed", increment=2)
    comps = (await db_session.scalars(
        select(GroupChallengeCompletion).where(GroupChallengeCompletion.challenge_id == ch.id)
    )).all()
    assert {comp.group_id for comp in comps} == {g1.id, g2.id}
    # A rewarded once only despite two group completions
    pa = await db_session.get(UserProgress, a.id)
    assert pa.xp == 10
    # B and C each rewarded via their group
    assert (await db_session.get(UserProgress, b.id)).xp == 10
    assert (await db_session.get(UserProgress, c.id)).xp == 10
