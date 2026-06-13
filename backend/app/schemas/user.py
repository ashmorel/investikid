import re
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.content import TOPIC_PATH_VALUES
from app.services.age_tier import AgeTier

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_SUPPORTED_REGIONS = {"US", "GB", "HK"}


class UserProfile(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    dob: date
    country_code: str
    currency_code: str
    topic_path: str | None
    content_region: str | None = None
    is_premium: bool
    push_enabled: bool = False
    biometric_allowed: bool = False
    is_admin: bool
    parent_email: str | None
    created_at: datetime
    email_verified_at: datetime | None = None
    age_tier: AgeTier = "explorer"

    model_config = {"from_attributes": True}


class UpdatePreferencesRequest(BaseModel):
    # country_code is intentionally NOT updatable here: it drives the
    # COPPA / UK-GDPR parental-consent regime (compliance.py / consent_service.py)
    # and is fixed at registration. Any country_code sent in the body is ignored.
    currency_code: str | None = None
    topic_path: str | None = Field(default=None, max_length=20)
    content_region: str | None = None

    @field_validator("currency_code", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("currency_code")
    @classmethod
    def validate_currency(cls, v):
        if v is None:
            return v
        if not _CURRENCY_RE.match(v):
            raise ValueError("currency_code must be a 3-letter ISO 4217 code")
        return v

    @field_validator("content_region", mode="before")
    @classmethod
    def uppercase_region(cls, v):
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("content_region")
    @classmethod
    def validate_region(cls, v):
        if v is None:
            return v
        if v not in _SUPPORTED_REGIONS:
            raise ValueError("content_region must be one of US, GB, HK")
        return v

    @field_validator("topic_path", mode="before")
    @classmethod
    def normalise_topic(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("topic_path")
    @classmethod
    def validate_topic(cls, v):
        if v is None:
            return v
        if v not in TOPIC_PATH_VALUES:
            raise ValueError("topic_path must be one of the known learning topics")
        return v


class UserProgressOut(BaseModel):
    xp: int
    level: int
    streak_count: int
    streak_freezes: int = 0
    last_activity_date: date | None
    daily_goal_xp: int = 30
    xp_today: int = 0
    goal_met: bool = False
    virtual_coins: int = 0


class DailyGoalUpdate(BaseModel):
    daily_goal_xp: Literal[10, 30, 50]
