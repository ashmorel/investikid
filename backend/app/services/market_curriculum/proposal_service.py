from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.content import Level, Module
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.types import CurriculumProposal, ValidationReport

_ACTIVE = ("proposed", "accepted")


async def save_proposal(
    session: AsyncSession, proposal: CurriculumProposal, report: ValidationReport
) -> MarketCurriculumProposal:
    await session.execute(
        update(MarketCurriculumProposal)
        .where(MarketCurriculumProposal.market_code == proposal.market_code,
               MarketCurriculumProposal.status.in_(_ACTIVE))
        .values(status="superseded")
    )
    row = MarketCurriculumProposal(
        market_code=proposal.market_code, status="proposed",
        proposal_json=proposal.model_dump(), coverage_json=report.model_dump(),
    )
    session.add(row)
    await session.flush()
    return row


async def get_active_proposal(
    session: AsyncSession, market_code: str
) -> MarketCurriculumProposal | None:
    return (await session.scalars(
        select(MarketCurriculumProposal)
        .where(MarketCurriculumProposal.market_code == market_code,
               MarketCurriculumProposal.status.in_(_ACTIVE))
        .order_by(MarketCurriculumProposal.created_at.desc())
    )).first()


async def accept_proposal(session: AsyncSession, row: MarketCurriculumProposal) -> dict:
    if row.status == "accepted":
        raise ValueError("proposal already accepted")
    proposal = CurriculumProposal.model_validate(row.proposal_json)
    n_modules = n_levels = 0
    tree = row.proposal_json
    # Sort the raw JSON the same way we iterate the validated proposal, so the
    # level_id write-back indices below can never misalign even if proposal_json
    # was ever stored out of order_index order.
    tree["modules"].sort(key=lambda m: m.get("order_index", 0))
    for mod in tree["modules"]:
        mod["levels"].sort(key=lambda lvl: lvl.get("order_index", 0))
    for m_idx, mod_node in enumerate(sorted(proposal.modules, key=lambda m: m.order_index)):
        module = Module(
            topic=mod_node.topic[:30], title=mod_node.title, country_codes=[],
            market_code=proposal.market_code, is_premium=False,
            order_index=mod_node.order_index, icon=mod_node.icon,
            min_age=mod_node.min_age, max_age=mod_node.max_age,
            published=False,  # staged — invisible until publish_market_curriculum swaps it live
        )
        session.add(module)
        await session.flush()
        n_modules += 1
        tree["modules"][m_idx]["module_id"] = str(module.id)
        for l_idx, lvl_node in enumerate(sorted(mod_node.levels, key=lambda lvl: lvl.order_index)):
            level = Level(
                module_id=module.id, title=lvl_node.title, order_index=lvl_node.order_index,
                is_premium=False, pass_threshold=0.7,
                learning_objectives=[lvl_node.learning_objective],
            )
            session.add(level)
            await session.flush()
            n_levels += 1
            tree["modules"][m_idx]["levels"][l_idx]["level_id"] = str(level.id)
    row.proposal_json = tree
    row.status = "accepted"
    row.accepted_at = datetime.now(UTC)
    # Re-assign the JSON attribute so SQLAlchemy tracks the in-place mutation.
    flag_modified(row, "proposal_json")
    await session.flush()
    return {"modules": n_modules, "levels": n_levels}
