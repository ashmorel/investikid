import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.market_curriculum.designer import (
    CurriculumDesignError,
    _system_prompt,
    design_curriculum,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_prompt_requests_tiered_concept_counts():
    prompt = _system_prompt("GB", {"currency": "GBP"})
    assert "tier-1 level has 5 concepts" in prompt
    assert "tier-2 level 8 concepts" in prompt
    assert "tier-3 level 10 concepts" in prompt

ALL = ["earning_income","spending_budgeting","saving_goals","banking_accounts",
       "borrowing_debt","growing_compound","risk_diversification","safety_scams","tax_giving"]

def _good_tree():
    levels = [{"title": f"L{i}", "order_index": i, "complexity_tier": 1 + i // 3,
               "learning_objective": "o", "concepts": ["c"], "backbone_keys": [k]}
              for i, k in enumerate(ALL)]
    return {"modules": [{"topic": "money", "title": "Money basics", "icon": "💵",
                         "min_age": 10, "max_age": 14, "order_index": 0, "levels": levels}]}

def _patch_llm(*returns):
    client = AsyncMock()
    client.complete = AsyncMock(side_effect=[json.dumps(r) for r in returns])
    return patch("app.services.market_curriculum.designer.get_llm_client", return_value=client), client

async def test_returns_valid_proposal_and_report():
    p_llm, client = _patch_llm(_good_tree())
    with p_llm:
        proposal, report = await design_curriculum("US", {"currency": "USD"})
    assert report.ok and proposal.market_code == "US"
    assert len(proposal.modules[0].levels) == 9
    assert client.complete.await_count == 1

async def test_retries_once_when_a_backbone_key_missing():
    bad = _good_tree()
    bad["modules"][0]["levels"] = bad["modules"][0]["levels"][:-1]
    p_llm, client = _patch_llm(bad, _good_tree())
    with p_llm:
        proposal, report = await design_curriculum("US", {"currency": "USD"})
    assert client.complete.await_count == 2 and report.ok

async def test_surfaces_residual_gaps_after_retry():
    bad = _good_tree()
    bad["modules"][0]["levels"] = bad["modules"][0]["levels"][:-1]
    p_llm, _ = _patch_llm(bad, bad)
    with p_llm:
        _, report = await design_curriculum("US", {"currency": "USD"})
    assert not report.ok and "tax_giving" in report.missing_backbone

async def test_raises_on_unparseable_output():
    p_llm, _ = _patch_llm("not json", "still not json")
    with p_llm, pytest.raises(CurriculumDesignError):
        await design_curriculum("US", {"currency": "USD"})
