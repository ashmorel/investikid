"""Cron-warm the shared market surfaces (featured quotes + movers) per region so
user requests hit Redis instead of fanning out to yfinance."""
from __future__ import annotations

import logging

from app.services.price_provider import REGION_EXCHANGES

logger = logging.getLogger(__name__)


def warm_all(provider) -> dict:
    """Warm every region. Best-effort: one region's failure never aborts the rest."""
    results = []
    for region in REGION_EXCHANGES:
        try:
            results.append(provider.warm_region(region))
        except Exception as exc:  # noqa: BLE001 — one region must not abort the batch
            logger.warning("warm_all failed for %s: %s", region, exc)
            results.append({"region": region, "error": True})
    return {"regions": results}
