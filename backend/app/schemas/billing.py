from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    plan: Literal["annual", "monthly"] = "annual"


class CheckoutResponse(BaseModel):
    url: str


class PlanOut(BaseModel):
    plan: str
    interval: str
    display_price: str
    savings_pct: int | None = None
    apple_product_id: str
    google_product_id: str


class PlansResponse(BaseModel):
    currency: str
    plans: list[PlanOut]


class PortalResponse(BaseModel):
    url: str


class SubscriptionStatusResponse(BaseModel):
    has_subscription: bool
    status: str | None = None
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
