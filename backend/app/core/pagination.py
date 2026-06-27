"""Keyset pagination for batch/cron jobs.

Crons that did ``(await session.execute(stmt)).all()`` over a whole table loaded
every eligible row into memory at once. ``iter_keyset`` streams the same rows in
fixed-size, keyset-ordered batches instead: memory stays bounded, and because
each batch is a *fresh* query (not a held server-side cursor) the loop body is
free to issue its own sub-queries / writes on the same session — which a server
cursor on asyncpg would forbid.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession


async def iter_keyset(
    session: AsyncSession,
    stmt: Select,
    *,
    key_col: Any,
    key_of: Callable[[Any], Any],
    batch_size: int = 500,
) -> AsyncIterator[Any]:
    """Yield the rows of ``stmt`` in keyset-paginated batches ordered by ``key_col``.

    ``key_col`` must be a sortable, unique-within-the-result column (a primary key,
    or a ``DISTINCT`` column). ``key_of`` extracts that key's value from a yielded
    row so the next batch can resume after it. The caller's ``stmt`` must not carry
    its own ``ORDER BY``/``LIMIT`` (this adds them).
    """
    last = None
    while True:
        q = stmt.order_by(key_col.asc()).limit(batch_size)
        if last is not None:
            q = q.where(key_col > last)
        rows = (await session.execute(q)).all()
        if not rows:
            return
        for row in rows:
            yield row
        if len(rows) < batch_size:
            return
        last = key_of(rows[-1])
