import pytest
from sqlalchemy import func, select

from app.models.content import Level, Module
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.proposal_service import (
    accept_proposal,
    get_active_proposal,
    save_proposal,
)
from app.services.market_curriculum.types import (
    CurriculumProposal,
    LevelNode,
    ModuleNode,
    ValidationReport,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

def _proposal():
    levels = [LevelNode(title="L0", order_index=0, complexity_tier=1,
                        learning_objective="o", concepts=["a", "b"], backbone_keys=["saving_goals"])]
    mod = ModuleNode(topic="money", title="Money", icon="💵", min_age=10, max_age=14,
                     order_index=0, levels=levels)
    return CurriculumProposal(market_code="US", modules=[mod])

_REPORT = ValidationReport(ok=True, missing_backbone=[], tiers_present=[1,2,3],
                           spans_all_tiers=True, regressions=[])

async def test_save_then_get_active(db_session):
    await save_proposal(db_session, _proposal(), _REPORT)
    row = await get_active_proposal(db_session, "US")
    assert row is not None and row.status == "proposed"

async def test_redesign_supersedes_prior(db_session):
    await save_proposal(db_session, _proposal(), _REPORT)
    await save_proposal(db_session, _proposal(), _REPORT)
    active = (await db_session.scalars(select(MarketCurriculumProposal).where(
        MarketCurriculumProposal.market_code == "US",
        MarketCurriculumProposal.status == "proposed"))).all()
    superseded = (await db_session.scalars(select(MarketCurriculumProposal).where(
        MarketCurriculumProposal.market_code == "US",
        MarketCurriculumProposal.status == "superseded"))).all()
    assert len(active) == 1 and len(superseded) == 1

async def test_accept_materialises_modules_and_levels(db_session):
    row = await save_proposal(db_session, _proposal(), _REPORT)
    result = await accept_proposal(db_session, row)
    assert result == {"modules": 1, "levels": 1}
    mods = (await db_session.scalars(select(Module).where(Module.market_code == "US"))).all()
    assert len(mods) == 1
    n_levels = await db_session.scalar(select(func.count(Level.id)).where(Level.module_id == mods[0].id))
    assert n_levels == 1
    # level_id written back into the stored tree
    assert row.status == "accepted" and row.accepted_at is not None
    assert row.proposal_json["modules"][0]["levels"][0]["level_id"] is not None

async def test_accept_twice_raises(db_session):
    row = await save_proposal(db_session, _proposal(), _REPORT)
    await accept_proposal(db_session, row)
    with pytest.raises(ValueError):
        await accept_proposal(db_session, row)
