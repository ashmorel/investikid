"""Auto-attach a single 'apply in the simulator' mission to the culminating lesson
of each investing-focused module, so investing lessons drive children into the
simulator with a rewarded, hands-on follow-up.

One mission per module (on the module's final lesson). Mission *completion* is
market-scoped in `simulator_rewards.evaluate_apply_missions`, so a child only ever
completes their own market's missions — without that scoping, a single first buy
would satisfy every market's `first_buy` mission at once and multiply the reward.

Re-running is idempotent (unique on `lesson_id`): an existing mission on the target
lesson is updated in place. `market_curriculum.publish` calls this after every
publish so a regenerated market re-acquires its missions (a republish replaces the
lessons, cascade-deleting the old missions).
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apply_mission import ApplyMission
from app.models.content import Lesson, Level, Module
from app.services.app_settings import (
    _FALLBACK_INVESTING_MISSION_CASH,
    get_investing_mission_cash,
)

logger = logging.getLogger(__name__)

MISSION_XP = 20

# (mission_type, params, title, prompt) keyed by the module's theme. Risk/diversify
# modules teach spreading money; growth/investing modules teach making a first buy.
_DIVERSIFY = (
    "diversify", {"n": 3}, "Build a diversified portfolio",
    "Head to the simulator and spread your money across 3 different stocks or funds.",
)
_FIRST_BUY = (
    "first_buy", {}, "Make your first investment",
    "Head to the simulator and buy your first stock or fund to put this lesson into action.",
)


def mission_spec_for_title(title: str) -> tuple[str, dict, str, str] | None:
    """Classify an investing module by title; None if it isn't an investing module."""
    t = (title or "").lower()
    if "risk" in t or "divers" in t:
        return _DIVERSIFY
    if any(k in t for k in ("invest", "stock", "fund", "grow", "compound")):
        return _FIRST_BUY
    return None


async def _culminating_lesson(session: AsyncSession, module_id) -> Lesson | None:
    """The module's final lesson: highest level order, then highest lesson order."""
    return (
        await session.execute(
            select(Lesson)
            .join(Level, Level.id == Lesson.level_id)
            .where(Lesson.module_id == module_id)
            .order_by(Level.order_index.desc(), Lesson.order_index.desc())
            .limit(1)
        )
    ).scalars().first()


async def sync_investing_missions(
    session: AsyncSession, *, market_code: str | None = None
) -> dict:
    """Create/refresh one simulator mission per live investing module.

    Scopes to `market_code` when given, else all markets. Does NOT commit — the
    caller owns the transaction. Returns a summary dict.
    """
    mod_q = select(Module).where(
        Module.published.is_(True), Module.archived_at.is_(None)
    )
    if market_code:
        mod_q = mod_q.where(Module.market_code == market_code.upper())
    modules = (await session.execute(mod_q)).scalars().all()

    cash_by_market = await get_investing_mission_cash(session)
    created = updated = 0
    for module in modules:
        spec = mission_spec_for_title(module.title)
        if spec is None:
            continue
        mission_type, params, title, prompt = spec
        lesson = await _culminating_lesson(session, module.id)
        if lesson is None:
            continue
        cash = cash_by_market.get(module.market_code, _FALLBACK_INVESTING_MISSION_CASH)
        existing = (
            await session.execute(
                select(ApplyMission).where(ApplyMission.lesson_id == lesson.id)
            )
        ).scalars().first()
        if existing is None:
            session.add(ApplyMission(
                lesson_id=lesson.id, mission_type=mission_type, params_json=params,
                title=title, prompt=prompt, xp_reward=MISSION_XP, cash_reward=cash,
            ))
            created += 1
        else:
            existing.mission_type = mission_type
            existing.params_json = params
            existing.title = title
            existing.prompt = prompt
            existing.xp_reward = MISSION_XP
            existing.cash_reward = cash
            updated += 1
    return {"created": created, "updated": updated}
