from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from datetime import date

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.user import User
from app.services.entitlements import set_premium
from app.services.retention import purge_expired_accounts


async def _session_scope() -> AsyncIterator:
    async with async_session_factory() as session:
        yield session


async def _grant_premium(argv: list[str]) -> int:
    args = [a for a in argv if a != "--revoke"]
    revoke = "--revoke" in argv
    if len(args) != 1:
        print("usage: python -m app.cli grant-premium <email|username> [--revoke]",
              file=sys.stderr)
        return 2
    ident = args[0].lower().strip()
    gen = _session_scope()
    session = await gen.__anext__()
    try:
        user = await session.scalar(
            select(User).where((User.email == ident) | (User.username == ident))
        )
        if user is None:
            print(f"user not found: {ident}", file=sys.stderr)
            return 2
        changed = await set_premium(
            session, user, value=not revoke, actor="cli"
        )
        await session.commit()
        verb = "revoked" if revoke else "granted"
        print(f"{verb} premium for {user.username}" if changed
              else f"no-op ({user.username} already {'free' if revoke else 'premium'})")
        return 0
    finally:
        await gen.aclose()


async def run(argv: list[str]) -> int:
    if not argv or argv[0] != "purge-accounts":
        if argv and argv[0] == "grant-premium":
            return await _grant_premium(argv[1:])
        print("usage: python -m app.cli {purge-accounts | grant-premium <email|username> [--revoke]}", file=sys.stderr)
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
