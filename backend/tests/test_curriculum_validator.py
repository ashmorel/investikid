from app.services.market_curriculum.types import CurriculumProposal, LevelNode, ModuleNode
from app.services.market_curriculum.validator import validate


def _mod(order, *levels):
    return ModuleNode(topic="t", title="M", icon="💵", min_age=10, max_age=14,
                      order_index=order, levels=list(levels))

def _lvl(order, tier, *keys):
    return LevelNode(title="L", order_index=order, complexity_tier=tier,
                     learning_objective="o", concepts=["c"], backbone_keys=list(keys))

ALL = ["earning_income","spending_budgeting","saving_goals","banking_accounts",
       "borrowing_debt","growing_compound","risk_diversification","safety_scams","tax_giving"]

def _full_proposal():
    # one level per backbone key, tiers spread 1→3, non-decreasing per key
    levels = [_lvl(i, 1 + i // 3, k) for i, k in enumerate(ALL)]
    return CurriculumProposal(market_code="US", modules=[_mod(0, *levels)])

def test_well_formed_proposal_passes():
    rep = validate(_full_proposal())
    assert rep.ok and rep.missing_backbone == [] and rep.spans_all_tiers

def test_missing_backbone_key_flagged():
    p = _full_proposal()
    p.modules[0].levels = p.modules[0].levels[:-1]  # drop tax_giving
    rep = validate(p)
    assert not rep.ok and "tax_giving" in rep.missing_backbone

def test_all_foundational_does_not_span_tiers():
    levels = [_lvl(i, 1, k) for i, k in enumerate(ALL)]
    rep = validate(CurriculumProposal(market_code="US", modules=[_mod(0, *levels)]))
    assert not rep.spans_all_tiers and not rep.ok

def test_tier_regression_flagged():
    # saving_goals appears at tier 3 then again later at tier 2 → regression
    levels = [_lvl(i, 1 + i // 3, k) for i, k in enumerate(ALL)]
    levels.append(_lvl(99, 2, "saving_goals"))
    levels[2] = _lvl(2, 3, "saving_goals")
    rep = validate(CurriculumProposal(market_code="US", modules=[_mod(0, *levels)]))
    assert not rep.ok and any("saving_goals" in r for r in rep.regressions)
