from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    status: str | None = None
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
