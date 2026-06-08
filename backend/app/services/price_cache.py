"""Fail-safe synchronous Redis cache for market data.

Used as an optional L2 behind LivePriceProvider's in-memory L1. Every operation
is wrapped so that if Redis is unreachable (local/CI/tests/not provisioned) the
cache silently no-ops and callers fall back to their existing behaviour.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_disabled = False


def _make_client() -> redis.Redis:
    # Patched in tests. Timeouts keep a dead Redis from blocking requests.
    return redis.from_url(
        settings.redis_url,
        socket_timeout=0.5,
        socket_connect_timeout=0.5,
        decode_responses=True,
    )


def _get_client() -> redis.Redis | None:
    global _client, _disabled
    if _disabled:
        return None
    if _client is None:
        try:
            _client = _make_client()
        except Exception:
            logger.debug("price_cache: client init failed; disabling", exc_info=True)
            _disabled = True
            return None
    return _client


def get_json(key: str) -> Any | None:
    global _disabled
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
    except Exception:
        logger.debug("price_cache: get failed; disabling", exc_info=True)
        _disabled = True
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    global _disabled
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except Exception:
        logger.debug("price_cache: set failed; disabling", exc_info=True)
        _disabled = True


def reset() -> None:
    """Test hook: clear the cached client + disabled flag."""
    global _client, _disabled
    _client = None
    _disabled = False
