import pytest
from sqlalchemy import select

from app.models.market_curriculum import MarketCurriculumProposal

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_can_persist_and_read_proposal(db_session):
    row = MarketCurriculumProposal(
        market_code="US", status="proposed",
        proposal_json={"market_code": "US", "modules": []},
        coverage_json={"ok": False, "missing_backbone": ["tax_giving"]},
    )
    db_session.add(row)
    await db_session.flush()
    got = (await db_session.scalars(
        select(MarketCurriculumProposal).where(MarketCurriculumProposal.market_code == "US")
    )).one()
    assert got.status == "proposed"
    assert got.coverage_json["missing_backbone"] == ["tax_giving"]
    assert got.accepted_at is None
