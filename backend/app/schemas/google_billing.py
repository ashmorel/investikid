from __future__ import annotations

from pydantic import BaseModel


class GoogleVerifyRequest(BaseModel):
    purchaseToken: str
    productId: str


class GoogleVerifyResponse(BaseModel):
    status: str = "ok"


class AccountTokenResponse(BaseModel):
    token: str
