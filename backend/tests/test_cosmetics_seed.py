"""TDD: cosmetics seed includes all types and is idempotent."""
import pytest
from sqlalchemy import select

from app.models.cosmetics import CosmeticItem
from app.seed.cosmetics import seed_cosmetics

pytestmark = pytest.mark.asyncio(loop_scope="session")

_EXPECTED_SLUGS = {
    # accessories (8)
    "party_hat", "sunglasses", "bow", "headphones",
    "grad_cap", "crown", "monocle", "top_hat",
    # backgrounds (5)
    "bg_beach", "bg_forest", "bg_city", "bg_space", "bg_vault",
    # skins (5)
    "skin_pink", "skin_sky", "skin_mint", "skin_gold", "skin_lavender",
    # limited drops (1)
    "founders_crown",
}


async def test_seed_has_new_categories_idempotent(db_session):
    await seed_cosmetics(db_session)
    await seed_cosmetics(db_session)  # idempotent
    rows = (await db_session.scalars(select(CosmeticItem))).all()
    types = {r.type for r in rows}
    assert {"accessory", "background", "skin"} <= types
    slugs = [r.slug for r in rows]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"
    assert _EXPECTED_SLUGS <= set(slugs), f"Missing: {_EXPECTED_SLUGS - set(slugs)}"
    assert len(rows) == 19, f"Expected 19 rows, got {len(rows)}"
