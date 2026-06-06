from decimal import Decimal

from app.services.simulator_rewards_config import (
    SIM_XP_DAILY_CAP,
    SIM_XP_PER_TRADE,
    MissionState,
    evaluate_mission,
)


def _state(distinct=0, sells=0, invested="0"):
    return MissionState(distinct_tickers=distinct, sell_count=sells, total_invested=Decimal(invested))


def test_config_values_are_positive():
    assert SIM_XP_PER_TRADE > 0
    assert SIM_XP_DAILY_CAP >= SIM_XP_PER_TRADE


def test_first_buy_satisfied_when_holding_exists():
    assert evaluate_mission("first_buy", {}, _state(distinct=1)) is True
    assert evaluate_mission("first_buy", {}, _state(distinct=0)) is False


def test_first_sell_satisfied_after_a_sell():
    assert evaluate_mission("first_sell", {}, _state(sells=1)) is True
    assert evaluate_mission("first_sell", {}, _state(sells=0)) is False


def test_diversify_requires_n_distinct():
    assert evaluate_mission("diversify", {"n": 3}, _state(distinct=3)) is True
    assert evaluate_mission("diversify", {"n": 3}, _state(distinct=2)) is False


def test_invest_amount_threshold():
    assert evaluate_mission("invest_amount", {"amount": "500"}, _state(invested="500")) is True
    assert evaluate_mission("invest_amount", {"amount": "500"}, _state(invested="499.99")) is False


def test_unknown_mission_type_is_false():
    assert evaluate_mission("nonexistent", {}, _state(distinct=99)) is False
