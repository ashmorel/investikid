import pytest
from sqlalchemy import select

from app.models.content import Module
from app.services.market_curriculum.proposal_service import accept_proposal, save_proposal
from app.services.market_curriculum.types import (
    CurriculumProposal,
    LevelNode,
    ModuleNode,
    ValidationReport,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

_REPORT = ValidationReport(ok=True, missing_backbone=[], tiers_present=[1, 2, 3],
                           spans_all_tiers=True, regressions=[])


def _proposal():
    lvl = LevelNode(title="L0", order_index=0, complexity_tier=1,
                    learning_objective="o", concepts=["a"], backbone_keys=["saving_goals"])
    mod = ModuleNode(topic="money", title="Money", icon="💵", min_age=10, max_age=14,
                     order_index=0, levels=[lvl])
    return CurriculumProposal(market_code="GB", modules=[mod])


async def test_accept_creates_unpublished_modules_and_records_ids(db_session):
    row = await save_proposal(db_session, _proposal(), _REPORT)
    await accept_proposal(db_session, row)
    mods = (await db_session.scalars(
        select(Module).where(Module.market_code == "GB", Module.title == "Money")
    )).all()
    assert len(mods) == 1
    assert mods[0].published is False  # staged, invisible to kids
    node = row.proposal_json["modules"][0]
    assert node["module_id"] == str(mods[0].id)
