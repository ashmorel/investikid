from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from datetime import date

from app.core.database import async_session_factory
from app.services.retention import purge_expired_accounts


async def _session_scope() -> AsyncIterator:
    async with async_session_factory() as session:
        yield session


async def run(argv: list[str]) -> int:
    if not argv or argv[0] != "purge-accounts":
        print("usage: python -m app.cli purge-accounts", file=sys.stderr)
        return 2
    gen = _session_scope()
    session = await gen.__anext__()
    try:
        n = await purge_expired_accounts(session, date.today())
        print(f"purged {n} account(s)")
        return 0
    finally:
        await gen.aclose()


def main() -> None:
    raise SystemExit(asyncio.run(run(sys.argv[1:])))


if __name__ == "__main__":
    main()
