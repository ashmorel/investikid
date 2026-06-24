"""Non-identifying display handles for public leaderboards (kids' safety).
Format: <Adjective><Animal><2 digits>, e.g. "CleverOtter42". Curated word
lists only — zero free text, so no moderation surface."""
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

ADJECTIVES = [
    "Clever", "Brave", "Sunny", "Swift", "Lucky", "Mighty", "Jolly", "Bright",
    "Cosmic", "Nimble", "Bouncy", "Cheery", "Dandy", "Epic", "Fuzzy", "Golden",
    "Happy", "Kind", "Lively", "Merry", "Noble", "Plucky", "Quick", "Rapid",
    "Snazzy", "Trusty", "Witty", "Zippy", "Breezy", "Curious",
]
ANIMALS = [
    "Otter", "Fox", "Panda", "Koala", "Tiger", "Falcon", "Dolphin", "Lynx",
    "Beaver", "Robin", "Badger", "Gecko", "Heron", "Ibis", "Jaguar", "Kestrel",
    "Llama", "Meerkat", "Newt", "Owl", "Puffin", "Quokka", "Raccoon", "Seal",
    "Toucan", "Pony", "Vole", "Walrus", "Yak", "Zebra",
]

def generate_handle() -> str:
    adj = secrets.choice(ADJECTIVES)
    animal = secrets.choice(ANIMALS)
    num = secrets.randbelow(90) + 10  # 10..99 — always 2 digits
    return f"{adj}{animal}{num}"

async def _handle_taken(session: AsyncSession, handle: str) -> bool:
    return (await session.scalar(select(User.id).where(User.display_handle == handle))) is not None

async def ensure_handle(session: AsyncSession, user: User) -> str:
    """Assign a unique handle if the user has none; return the current handle.
    Caller commits."""
    if user.display_handle:
        return user.display_handle
    for _ in range(20):
        candidate = generate_handle()
        if not await _handle_taken(session, candidate):
            user.display_handle = candidate
            await session.flush()
            return candidate
    raise RuntimeError("could not allocate a unique handle")
