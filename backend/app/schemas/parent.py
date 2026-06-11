import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr

from app.schemas.content import StandardRef


class ParentMagicLinkRequest(BaseModel):
    email: EmailStr


class RecentLessonOut(BaseModel):
    title: str
    type: str
    score: float | None
    completed_at: datetime


class BadgeOut(BaseModel):
    name: str
    icon: str
    earned_at: datetime


class LevelProgressOut(BaseModel):
    level_id: uuid.UUID
    title: str
    state: str  # "in_progress" | "completed" | "locked"
    locked_reason: str | None  # "premium" | "progression" | None
    passed: bool
    lessons_completed: int
    lessons_total: int
    mastered_at: datetime | None = None


class ModuleProgressOut(BaseModel):
    module_id: uuid.UUID
    title: str
    icon: str
    lessons_completed: int
    lessons_total: int
    levels: list[LevelProgressOut]
    standards_alignment: list[StandardRef] | None = None


class ChildAnalyticsOut(BaseModel):
    level: int
    xp: int
    xp_to_next_level: int
    streak_count: int
    lessons_completed: int
    lessons_total: int
    recent_lessons: list[RecentLessonOut]
    badges: list[BadgeOut]
    modules_progress: list[ModuleProgressOut] = []


class ChildOut(BaseModel):
    user_id: uuid.UUID
    username: str
    country_code: str
    is_active: bool
    is_premium: bool
    parent_consent_given_at: datetime | None
    consent_declined_at: datetime | None
    deleted_at: datetime | None
    deletion_requested_at: datetime | None
    age_tier: str
    tier_override: str | None = None
    analytics: ChildAnalyticsOut | None = None


class FreezeRequest(BaseModel):
    frozen: bool


class TierOverrideRequest(BaseModel):
    tier_override: Literal["explorer", "investor"] | None


class TierOverrideOut(BaseModel):
    tier_override: str | None
    age_tier: str


class PremiumToggleRequest(BaseModel):
    premium: bool


class PremiumRequestOut(BaseModel):
    id: uuid.UUID
    child_username: str
    context_kind: str
    context_label: str
    created_at: datetime


class OAuthSignInRequest(BaseModel):
    id_token: str
    nonce: str


class IdentityOut(BaseModel):
    provider: str
    parent_email: str
