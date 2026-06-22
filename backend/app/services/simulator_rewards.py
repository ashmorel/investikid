"""Reward engine for simulator activity: capped trade XP, mission evaluation, cash grants."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apply_mission import ApplyMission, ApplyMissionCompletion
from app.models.cash_grant import CashGrant
from app.models.content import Lesson, Module
from app.models.simulator import Holding, Portfolio, Trade
from app.models.user import UserProgress
from app.services.market_progress_service import award_xp
from app.services.simulator_rewards_config import (
    DEFAULT_MISSION_XP,
    SIM_XP_DAILY_CAP,
    SIM_XP_PER_TRADE,
    MissionState,
    evaluate_mission,
)


async def award_trade_xp(
    session: AsyncSession, progress: UserProgress, today_local: date
) -> int:
    """Award capped routine-trade XP. Resets the daily tally on date rollover.

    Returns the XP actually awarded (0 if already at the daily cap). Mutates `progress`.
    """
    if progress.sim_xp_date != today_local:
        progress.sim_xp_date = today_local
        progress.sim_xp_today = 0
    remaining = SIM_XP_DAILY_CAP - progress.sim_xp_today
    if remaining <= 0:
        return 0
    awarded = min(SIM_XP_PER_TRADE, remaining)
    progress.sim_xp_today += awarded
    await award_xp(session, progress, awarded)
    return awarded


async def grant_cash(
    session: AsyncSession,
    user_id: uuid.UUID,
    portfolio: Portfolio,
    source_type: str,
    source_id: uuid.UUID | None,
    amount: Decimal,
) -> bool:
    """Idempotently grant virtual cash. Returns True if granted, False if already granted.

    One-time sources (module/mission) are deduped by the (user, source_type, source_id) unique
    constraint via a SAVEPOINT. Admin top-ups pass source_id=None and are always applied.
    """
    if amount is None or amount <= 0:
        return False
    if source_id is not None:
        try:
            async with session.begin_nested():
                session.add(CashGrant(
                    user_id=user_id, source_type=source_type, source_id=source_id,
                    currency_code=portfolio.currency_code, amount=amount,
                ))
                await session.flush()
        except IntegrityError:
            # SAVEPOINT rollback keeps the outer transaction usable -> already granted.
            return False
    else:
        session.add(CashGrant(
            user_id=user_id, source_type=source_type, source_id=None,
            currency_code=portfolio.currency_code, amount=amount,
        ))
    portfolio.virtual_cash += amount
    return True


async def _mission_state(session: AsyncSession, portfolio: Portfolio) -> MissionState:
    distinct = await session.scalar(
        select(func.count(func.distinct(Holding.ticker))).where(Holding.portfolio_id == portfolio.id)
    )
    sells = await session.scalar(
        select(func.count(Trade.id)).where(Trade.portfolio_id == portfolio.id, Trade.type == "sell")
    )
    invested = await session.scalar(
        select(func.coalesce(func.sum(Trade.shares * Trade.price), 0)).where(
            Trade.portfolio_id == portfolio.id, Trade.type == "buy"
        )
    )
    return MissionState(
        distinct_tickers=int(distinct or 0),
        sell_count=int(sells or 0),
        total_invested=Decimal(str(invested or 0)),
    )


async def evaluate_apply_missions(
    session: AsyncSession,
    user_id: uuid.UUID,
    progress: UserProgress,
    portfolio: Portfolio,
    market_code: str | None = None,
) -> list[ApplyMission]:
    """Complete any newly-satisfied apply-missions. Awards XP + cash; returns completed missions.

    When `market_code` is given, only missions whose lesson belongs to a module in
    that market are considered — so a child completes only their own market's
    missions. (Mission predicates read global portfolio state, so without this scope a
    single first buy would satisfy every market's `first_buy` mission at once and
    multiply the reward.) `None` keeps the legacy all-markets behaviour.

    Badge awarding (mission.badge_id) is handled by the caller after this returns, so the badge
    service stays the single owner of UserBadge inserts.
    """
    completed_ids = set(
        (await session.execute(
            select(ApplyMissionCompletion.mission_id).where(ApplyMissionCompletion.user_id == user_id)
        )).scalars().all()
    )
    mission_q = select(ApplyMission)
    if market_code is not None:
        mission_q = (
            mission_q.join(Lesson, Lesson.id == ApplyMission.lesson_id)
            .join(Module, Module.id == Lesson.module_id)
            .where(Module.market_code == market_code)
        )
    missions = (await session.execute(mission_q)).scalars().all()
    pending = [m for m in missions if m.id not in completed_ids]
    if not pending:
        return []
    state = await _mission_state(session, portfolio)
    newly: list[ApplyMission] = []
    for mission in pending:
        if not evaluate_mission(mission.mission_type, mission.params_json, state):
            continue
        try:
            async with session.begin_nested():
                session.add(ApplyMissionCompletion(user_id=user_id, mission_id=mission.id))
                await session.flush()
        except IntegrityError:
            # Raced on the unique constraint; SAVEPOINT rollback keeps the outer txn usable.
            continue
        xp = mission.xp_reward or DEFAULT_MISSION_XP
        await award_xp(session, progress, xp)
        if mission.cash_reward:
            await grant_cash(session, user_id, portfolio, "mission", mission.id, mission.cash_reward)
        newly.append(mission)
    return newly
