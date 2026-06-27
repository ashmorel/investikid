"""Assemble the Simulator-entry snapshot (region featured quotes + movers) from
the warm cache. Never raises — a provider failure degrades to static fallbacks."""
from __future__ import annotations

import logging

from app.services.price_provider import (
    _FEATURED,
    REGION_EXCHANGES,
    _mover_to_dict,
    _quote_to_dict,
)

logger = logging.getLogger(__name__)


def snapshot(provider, region: str) -> dict:
    exchanges = REGION_EXCHANGES.get(region, [])
    featured_keys = [(t, e) for (t, e) in _FEATURED if e in exchanges]

    featured = []
    for t, e in featured_keys:
        try:
            featured.append(_quote_to_dict(provider.get_quote(t, e)))
        except Exception:
            logger.warning("snapshot: quote failed for %s:%s", t, e)

    try:
        movers_raw = provider.get_market_movers(region)
    except Exception:
        logger.warning("snapshot: movers failed for %s", region)
        movers_raw = {}

    movers = {
        exch: {
            "winners": [_mover_to_dict(m) for m in side.get("winners", [])],
            "losers": [_mover_to_dict(m) for m in side.get("losers", [])],
        }
        for exch, side in movers_raw.items()
    }
    return {"region": region, "featured": featured, "movers": movers}
