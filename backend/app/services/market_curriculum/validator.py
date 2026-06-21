from app.services.market_curriculum.backbone import backbone_keys
from app.services.market_curriculum.types import CurriculumProposal, ValidationReport


def _ordered_levels(proposal: CurriculumProposal):
    """All levels flattened in curriculum order (module order, then level order)."""
    out = []
    for module in sorted(proposal.modules, key=lambda m: m.order_index):
        for level in sorted(module.levels, key=lambda lvl: lvl.order_index):
            out.append(level)
    return out


def validate(proposal: CurriculumProposal) -> ValidationReport:
    levels = _ordered_levels(proposal)
    covered: set[str] = set()
    tiers: set[int] = set()
    last_tier_for_key: dict[str, int] = {}
    regressions: list[str] = []

    for level in levels:
        tiers.add(level.complexity_tier)
        for key in level.backbone_keys:
            covered.add(key)
            prev = last_tier_for_key.get(key)
            if prev is not None and level.complexity_tier < prev:
                regressions.append(
                    f"{key} regresses from tier {prev} to {level.complexity_tier}"
                )
            last_tier_for_key[key] = max(level.complexity_tier, prev or 0)

    missing = sorted(backbone_keys() - covered)
    spans_all_tiers = {1, 2, 3}.issubset(tiers)
    ok = not missing and spans_all_tiers and not regressions
    return ValidationReport(
        ok=ok, missing_backbone=missing, tiers_present=sorted(tiers),
        spans_all_tiers=spans_all_tiers, regressions=regressions,
    )
