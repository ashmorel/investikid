import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BadgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str
    icon_url: str
    earned_at: datetime | None = None


class BadgeDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    description: str
    icon_url: str
    condition_type: str
    condition_value: int
    earned_at: None = None


class ChallengeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    description: str
    type: str
    target_value: int
    xp_reward: int
    starts_at: datetime
    ends_at: datetime
    is_premium: bool
    progress: int = 0
    completed_at: datetime | None = None


class LeaderboardRowOut(BaseModel):
    rank: int
    name: str
    country_code: str | None = None
    points: int
    is_me: bool
