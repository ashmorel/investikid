"""Production-only daily cache for expensive per-request LLM outputs.

The home greeting and the personalised news summary each call an LLM on every
request, so cost grows linearly with traffic even though the output is stable
for a given input over a day. Cache the result in Redis (reusing the fail-safe
``price_cache`` client) keyed by caller-supplied parts plus the UTC day, so the
key rolls over naturally at midnight.

Production-only: dev/staging/test have no provisioned Redis (and gating here
keeps caching out of the test path entirely, avoiding cross-test leakage) —
mirrors the leaderboard cache and rate-limiter gates. Every operation no-ops
outside production, so callers always fall back to generating live.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.services import price_cache


def _enabled() -> bool:
    from app.core.config import settings
    return settings.environment == "production"


def _key(surface: str, parts: list[str]) -> str:
    day = datetime.now(UTC).date().isoformat()
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]
    return f"llm:{surface}:{day}:{digest}"


def get(surface: str, parts: list[str]) -> Any | None:
    """Return the cached value for (surface, parts) on this UTC day, or None."""
    if not _enabled():
        return None
    return price_cache.get_json(_key(surface, parts))


def put(surface: str, parts: list[str], value: Any, ttl_seconds: int) -> None:
    """Cache a JSON-serialisable value for (surface, parts) on this UTC day."""
    if not _enabled():
        return
    price_cache.set_json(_key(surface, parts), value, ttl_seconds)
