"""Market helpers.

``active_market(user)`` centralises the ``user.active_market_code or "GB"``
fallback that was duplicated across the arcade/quiz/moneyword services.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

DEFAULT_MARKET = "GB"


def active_market(user: User) -> str:
    """The user's active market code, defaulting to GB when unset."""
    return user.active_market_code or DEFAULT_MARKET
