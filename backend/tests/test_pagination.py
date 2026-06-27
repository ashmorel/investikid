from datetime import date

import pytest
from sqlalchemy import select

from app.core.pagination import iter_keyset
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_iter_keyset_covers_all_rows_exactly_once(db_session):
    """With batch_size smaller than the row count, every matching row is yielded
    exactly once across the batch boundary (no omissions, no duplicates)."""
    made = []
    for i in range(5):
        u = User(username=f"pg_{i}", password_hash="x", dob=date(2012, 1, 1),
                 country_code="GB", currency_code="GBP")
        db_session.add(u)
        made.append(u)
    await db_session.flush()
    made_ids = {u.id for u in made}

    stmt = select(User).where(User.username.like("pg\\_%", escape="\\"))
    seen: list = []
    async for (u,) in iter_keyset(db_session, stmt, key_col=User.id,
                                  key_of=lambda r: r[0].id, batch_size=2):
        seen.append(u.id)

    assert len(seen) == 5            # all rows, despite batch_size=2
    assert len(set(seen)) == 5       # no row yielded twice at a batch edge
    assert set(seen) == made_ids


async def test_iter_keyset_empty_result_is_safe(db_session):
    stmt = select(User).where(User.username == "definitely-not-present-xyz")
    seen = [row async for row in iter_keyset(db_session, stmt, key_col=User.id,
                                             key_of=lambda r: r[0].id)]
    assert seen == []
