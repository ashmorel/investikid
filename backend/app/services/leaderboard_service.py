"""Unified weekly leaderboard: scope (market/global/friends) × metric (xp/arcade).
Public scopes show display_handle and only consented, non-hidden children.
Friends shows usernames for all group members (closed, parent-created)."""
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade import ArcadeScore
from app.models.content import Lesson, LessonCompletion
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.group import GroupMembership
from app.models.user import User

Scope = Literal["market", "global", "friends"]
Metric = Literal["xp", "arcade"]


@dataclass
class AvatarData:
    skin: str | None
    accessories: list[str] = field(default_factory=list)


@dataclass
class LeaderboardRow:
    rank: int
    name: str
    country_code: str | None
    points: int
    is_me: bool
    avatar: AvatarData = field(default_factory=lambda: AvatarData(skin=None, accessories=[]))


def _monday(now: datetime) -> datetime:
    return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


async def _avatars_for(session, user_ids: list) -> dict:
    """Map user_id -> AvatarData(equipped skin + accessory slugs). One query."""
    if not user_ids:
        return {}
    stmt = (
        select(UserCosmetic.user_id, CosmeticItem.type, CosmeticItem.slug)
        .join(CosmeticItem, CosmeticItem.id == UserCosmetic.item_id)
        .where(UserCosmetic.equipped.is_(True), UserCosmetic.user_id.in_(user_ids))
        .order_by(UserCosmetic.user_id, CosmeticItem.slug)
    )
    out: dict = {}
    for uid, ctype, slug in (await session.execute(stmt)).all():
        a = out.setdefault(uid, AvatarData(skin=None, accessories=[]))
        if ctype == "skin":
            a.skin = slug
        elif ctype == "accessory":
            a.accessories.append(slug)
    return out


def _metric_join(stmt, metric: Metric, since: datetime):
    """Attach the metric's sum + time filter to a select over User."""
    if metric == "xp":
        total = func.coalesce(func.sum(Lesson.xp_reward), 0)
        stmt = (
            stmt.outerjoin(LessonCompletion,
                           and_(LessonCompletion.user_id == User.id,
                                LessonCompletion.completed_at >= since))
                .outerjoin(Lesson, Lesson.id == LessonCompletion.lesson_id)
        )
    else:
        total = func.coalesce(func.sum(ArcadeScore.points), 0)
        stmt = stmt.outerjoin(ArcadeScore,
                              and_(ArcadeScore.user_id == User.id,
                                   ArcadeScore.created_at >= since))
    return stmt, total


async def leaderboard(session: AsyncSession, *, viewer: User, scope: Scope,
                      metric: Metric, limit: int = 50) -> list[LeaderboardRow]:
    since = _monday(datetime.now(UTC))

    if scope == "friends":
        return await _friends(session, viewer=viewer, metric=metric, since=since)

    # public (market/global): handle identity, consent-gated population
    base = select(User.id, User.display_handle, User.country_code)
    base, total = _metric_join(base, metric, since)
    base = base.where(User.leaderboard_consent.is_(True), User.leaderboard_hidden.is_(False))
    if scope == "market":
        base = base.where(User.active_market_code == viewer.active_market_code)
    base = base.group_by(User.id, User.display_handle, User.country_code)
    base = base.order_by(total.desc(), User.display_handle.asc()).limit(limit)

    rows = (await session.execute(base.add_columns(total.label("pts")))).all()
    avatars = await _avatars_for(session, [uid for (uid, *_rest) in rows])
    out = [
        LeaderboardRow(rank=i + 1, name=handle or "—", country_code=cc,
                       points=int(pts), is_me=(uid == viewer.id),
                       avatar=avatars.get(uid, AvatarData(None, [])))
        for i, (uid, handle, cc, pts) in enumerate(rows)
    ]
    # Ensure the viewer always sees their own row (even if not public / outside top-N).
    if not any(r.is_me for r in out):
        out.append(await _own_row(session, viewer=viewer, scope=scope, metric=metric, since=since))
    return out


async def _own_row(session, *, viewer, scope, metric, since) -> LeaderboardRow:
    mine = select(User.id)
    mine, total = _metric_join(mine, metric, since)
    mine = mine.where(User.id == viewer.id).group_by(User.id)
    pts = (await session.execute(mine.add_columns(total.label("pts")))).first()
    points = int(pts.pts) if pts else 0
    # rank = how many public users beat me + 1 (cheap COUNT over the same population)
    pop = select(User.id)
    pop, ptotal = _metric_join(pop, metric, since)
    pop = pop.where(User.leaderboard_consent.is_(True), User.leaderboard_hidden.is_(False))
    if scope == "market":
        pop = pop.where(User.active_market_code == viewer.active_market_code)
    pop = pop.group_by(User.id).having(ptotal > points)
    ahead = len((await session.execute(pop)).all())
    av = (await _avatars_for(session, [viewer.id])).get(viewer.id, AvatarData(None, []))
    return LeaderboardRow(rank=ahead + 1, name=viewer.display_handle or "—",
                          country_code=viewer.country_code, points=points, is_me=True, avatar=av)


async def _friends(session, *, viewer, metric, since) -> list[LeaderboardRow]:
    group_ids = (await session.scalars(
        select(GroupMembership.group_id).where(GroupMembership.user_id == viewer.id))).all()
    if not group_ids:
        return []
    base = select(User.id, User.username, User.country_code)
    base, total = _metric_join(base, metric, since)
    base = (base.join(GroupMembership, GroupMembership.user_id == User.id)
                .where(GroupMembership.group_id.in_(group_ids))
                .group_by(User.id, User.username, User.country_code)
                .order_by(total.desc(), User.username.asc()))
    rows = (await session.execute(base.add_columns(total.label("pts")))).all()
    avatars = await _avatars_for(session, [uid for (uid, *_rest) in rows])
    return [
        LeaderboardRow(rank=i + 1, name=uname, country_code=cc,
                       points=int(pts), is_me=(uid == viewer.id),
                       avatar=avatars.get(uid, AvatarData(None, [])))
        for i, (uid, uname, cc, pts) in enumerate(rows)
    ]
