from app.models.content import Level, Module
from app.services.admin_content_generation_service import _system_prompt
from app.services.market_curriculum.proposal_service import _slugify_topic


def test_slugify_topic_normalises_labels():
    assert _slugify_topic("Earning & Income") == "earning_income"
    assert _slugify_topic("  Growing Money  ") == "growing_money"
    assert _slugify_topic("Risk & Diversification") == "risk_diversification"
    assert _slugify_topic("!!!") == "general"
    assert _slugify_topic("") == "general"


def _mod():
    return Module(topic="saving", title="Saving", market_code="GB", is_premium=False,
                  order_index=0, icon="💷", min_age=10, max_age=14, country_codes=[])


def _lvl():
    return Level(title="Level 1", order_index=0, is_premium=False, pass_threshold=0.7)


def test_system_prompt_carries_concision_and_penny_rules():
    p = _system_prompt("card", _mod(), _lvl())
    assert "45-65 words" in p
    assert "years 8-10" in p
    assert "Coach Penny" in p
