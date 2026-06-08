from typing import Literal

from pydantic import BaseModel


class ChildSummary(BaseModel):
    username: str
    age: int
    country_code: str


class ConsentDecision(BaseModel):
    decision: Literal["approve", "decline"]
    attest_guardian: bool = False
