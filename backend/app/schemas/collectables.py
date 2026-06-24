from pydantic import BaseModel


class GoalOut(BaseModel):
    type: str
    threshold: int
    current: int


class DropOut(BaseModel):
    slug: str
    name: str
    emoji: str
    type: str
    rarity: str | None
    ends_at: str | None
    goal: GoalOut
    earned: bool


class OwnedOut(BaseModel):
    slug: str
    name: str
    emoji: str
    type: str
    rarity: str | None
    equipped: bool


class CollectablesResponse(BaseModel):
    active: list[DropOut]
    owned: list[OwnedOut]
