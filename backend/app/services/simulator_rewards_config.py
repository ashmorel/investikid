"""Central, developer-tuned config for simulator rewards (deploy to change).

Money amounts (starting cash, per-module/per-mission rewards) are NOT here — those are
runtime-editable in the admin panel. This module holds only the anti-gaming mechanics
and the mission-type predicate registry.
"""
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

# Anti-gaming mechanics
SIM_XP_PER_TRADE: int = 5          # XP per routine trade
SIM_XP_DAILY_CAP: int = 25         # max routine-trade XP per local day
DEFAULT_MISSION_XP: int = 20       # used when an ApplyMission.xp_reward is 0


@dataclass(frozen=True)
class MissionState:
    """Snapshot of a portfolio used to evaluate mission predicates."""
    distinct_tickers: int      # number of distinct currently-held tickers
    sell_count: int            # number of sell trades ever executed
    total_invested: Decimal    # sum of buy cost basis ever (shares * price on buys)


def _first_buy(_params: dict, s: MissionState) -> bool:
    return s.distinct_tickers >= 1


def _first_sell(_params: dict, s: MissionState) -> bool:
    return s.sell_count >= 1


def _diversify(params: dict, s: MissionState) -> bool:
    return s.distinct_tickers >= int(params.get("n", 1))


def _invest_amount(params: dict, s: MissionState) -> bool:
    return s.total_invested >= Decimal(str(params.get("amount", "0")))


# Registry: mission_type -> predicate. Add new mission types here.
MISSION_PREDICATES: dict[str, Callable[[dict, MissionState], bool]] = {
    "first_buy": _first_buy,
    "first_sell": _first_sell,
    "diversify": _diversify,
    "invest_amount": _invest_amount,
}

# Values surfaced to the admin UI for the mission-type dropdown.
MISSION_TYPES: tuple[str, ...] = tuple(MISSION_PREDICATES.keys())


def evaluate_mission(mission_type: str, params: dict, state: MissionState) -> bool:
    predicate = MISSION_PREDICATES.get(mission_type)
    if predicate is None:
        return False
    return predicate(params or {}, state)
