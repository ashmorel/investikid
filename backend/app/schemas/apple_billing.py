from __future__ import annotations

from pydantic import BaseModel


class AppleVerifyRequest(BaseModel):
    jws: str


class AppleVerifyResponse(BaseModel):
    status: str = "ok"


class AppleAccountTokenResponse(BaseModel):
    token: str
