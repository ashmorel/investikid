import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion
from app.models.group import GroupMembership, LeaderboardGroup
from app.models.user import User
from app.services.group_config import (
    GROUP_CODE_ALPHABET,
    GROUP_CODE_LENGTH,
    GROUP_SIZE_CAP,
    GROUPS_PER_PARENT_CAP,
    LEADERBOARD_WEEK_START_WEEKDAY,
)

_CODE_RETRIES = 8


class GroupNotFound(Exception):
    pass


class GroupLimitError(Exception):
    pass


def _random_code() -> str:
    return "".join(secrets.choice(GROUP_CODE_ALPHABET) for _ in range(GROUP_CODE_LENGTH))


async def _generate_unique_code(session: AsyncSession) -> str:
    for _ in range(_CODE_RETRIES):
        code = _random_code()
        exists = await session.scalar(select(LeaderboardGroup.id).where(LeaderboardGroup.code == code))
        if exists is None:
            return code
    raise GroupLimitError("could not generate a unique code")


async def create_group(session: AsyncSession, owner_parent_email: str, name: str) -> LeaderboardGroup:
    owned = await session.scalar(
        select(func.count(LeaderboardGroup.id)).where(LeaderboardGroup.owner_parent_email == owner_parent_email)
    )
    if owned >= GROUPS_PER_PARENT_CAP:
        raise GroupLimitError("too many groups")
    code = await _generate_unique_code(session)
    group = LeaderboardGroup(name=name, code=code, owner_parent_email=owner_parent_email)
    session.add(group)
    await session.flush()
    return group


async def join_child(session: AsyncSession, code: str, child: User, parent_email: str) -> LeaderboardGroup:
    group = await session.scalar(select(LeaderboardGroup).where(LeaderboardGroup.code == code))
    if group is None:
        raise GroupNotFound("unknown code")
    existing = await session.scalar(
        select(GroupMembership.id).where(
            GroupMembership.group_id == group.id, GroupMembership.user_id == child.id
        )
    )
    if existing is not None:
        return group
    member_count = await session.scalar(
        select(func.count(GroupMembership.id)).where(GroupMembership.group_id == group.id)
    )
    if member_count >= GROUP_SIZE_CAP:
        raise GroupLimitError("group is full")
    try:
        # The SAVEPOINT is what protects the outer transaction under a concurrent-join
        # race; that path isn't reproducible single-threaded (the `existing` pre-check
        # short-circuits), but on Postgres a bare flush()-then-swallow would poison the
        # whole transaction once IntegrityError fires.
        async with session.begin_nested():
            session.add(GroupMembership(group_id=group.id, user_id=child.id, added_by_parent_email=parent_email))
            await session.flush()
    except IntegrityError:
        # Lost a concurrent join race on the unique constraint; the SAVEPOINT rollback
        # keeps the outer transaction usable -> treat as already a member.
        pass
    return group


async def remove_member(session: AsyncSession, group_id: uuid.UUID, child_user_id: uuid.UUID) -> None:
    await session.execute(
        delete(GroupMembership).where(
            GroupMembership.group_id == group_id, GroupMembership.user_id == child_user_id
        )
    )


async def delete_group(session: AsyncSession, group: LeaderboardGroup) -> None:
    await session.delete(group)


def _week_start(now: datetime) -> datetime:
    days_since = (now.weekday() - LEADERBOARD_WEEK_START_WEEKDAY) % 7
    return (now - timedelta(days=days_since)).replace(hour=0, minute=0, second=0, microsecond=0)


async def group_leaderboard_for_child(session: AsyncSession, child_user_id: uuid.UUID) -> list[dict]:
    """For each group the child belongs to, return members + weekly XP (members with no
    activity appear with 0), ordered by xp desc. Marks the requesting child with is_me."""
    group_ids = (await session.scalars(
        select(GroupMembership.group_id).where(GroupMembership.user_id == child_user_id)
    )).all()
    if not group_ids:
        return []

    week_start = _week_start(datetime.now(UTC))
    boards: list[dict] = []
    groups = (await session.scalars(
        select(LeaderboardGroup).where(LeaderboardGroup.id.in_(group_ids))
        .order_by(LeaderboardGroup.created_at)
    )).all()
    for group in groups:
        xp_expr = func.coalesce(func.sum(Lesson.xp_reward), 0).label("xp_this_week")
        stmt = (
            select(User.id, User.username, xp_expr)
            .join(GroupMembership, GroupMembership.user_id == User.id)
            .outerjoin(
                LessonCompletion,
                (LessonCompletion.user_id == User.id) & (LessonCompletion.completed_at >= week_start),
            )
            .outerjoin(Lesson, Lesson.id == LessonCompletion.lesson_id)
            .where(GroupMembership.group_id == group.id)
            .group_by(User.id, User.username)
            .order_by(xp_expr.desc(), User.username.asc())
        )
        rows = (await session.execute(stmt)).all()
        boards.append({
            "group_id": group.id,
            "group_name": group.name,
            "entries": [
                {"username": uname, "xp_this_week": int(xp), "is_me": uid == child_user_id}
                for uid, uname, xp in rows
            ],
        })
    return boards
