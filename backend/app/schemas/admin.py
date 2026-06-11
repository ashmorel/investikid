from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.content import SourceRef, StandardRef
from app.services.simulator_rewards_config import MISSION_TYPES

NonEmptyStr = Annotated[str, Field(min_length=1)]


# ── Apply mission ───────────────────────────────────────────────────
class ApplyMissionIn(BaseModel):
    mission_type: str
    params_json: dict = {}
    title: str
    prompt: str
    xp_reward: int = 0
    cash_reward: Decimal | None = None
    badge_id: uuid.UUID | None = None

    @field_validator("mission_type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in MISSION_TYPES:
            raise ValueError(f"unknown mission_type: {v}")
        return v


class ApplyMissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    mission_type: str
    params_json: dict
    title: str
    prompt: str
    xp_reward: int
    cash_reward: Decimal | None
    badge_id: uuid.UUID | None


# ── Module ──────────────────────────────────────────────────────────
class ModuleCreate(BaseModel):
    topic: str
    title: str
    icon: str = "📚"
    is_premium: bool = False
    country_codes: list[str] = []
    order_index: int
    prerequisite_ids: list[uuid.UUID] = []
    min_age: int | None = None
    max_age: int | None = None
    completion_cash_reward: Decimal | None = None

    @model_validator(mode="after")
    def validate_age_range(self):
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age must be less than or equal to max_age")
        return self


class ModuleUpdate(BaseModel):
    topic: str | None = None
    title: str | None = None
    icon: str | None = None
    is_premium: bool | None = None
    country_codes: list[str] | None = None
    prerequisite_ids: list[uuid.UUID] | None = None
    min_age: int | None = None
    max_age: int | None = None
    completion_cash_reward: Decimal | None = None
    standards_alignment: list[StandardRef] | None = None
    sources: list[SourceRef] | None = None


class ModuleOut(BaseModel):
    id: uuid.UUID
    topic: str
    title: str
    icon: str
    is_premium: bool
    country_codes: list[str]
    order_index: int
    lesson_count: int = 0
    prerequisite_ids: list[uuid.UUID] = []
    min_age: int | None = None
    max_age: int | None = None
    completion_cash_reward: Decimal | None = None
    standards_alignment: list[StandardRef] | None = None
    sources: list[SourceRef] | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Lesson ──────────────────────────────────────────────────────────
def validate_lesson_content_json(lesson_type: str, v: dict) -> None:
    """Per-type content_json rules. Raises ValueError on invalid. Shared by the
    admin LessonCreate validator AND the AI generation service."""
    if lesson_type == "card":
        if "title" not in v or "body" not in v:
            raise ValueError("Card requires title and body")
    elif lesson_type == "quiz":
        for key in ("question", "choices", "answer_index", "explanation"):
            if key not in v:
                raise ValueError(f"Quiz requires {key}")
        if not isinstance(v["choices"], list) or len(v["choices"]) < 2:
            raise ValueError("Quiz requires at least 2 choices")
        if not (0 <= v["answer_index"] < len(v["choices"])):
            raise ValueError("Invalid answer_index — must be within choices range")
    elif lesson_type == "scenario":
        for key in ("prompt", "choices", "correct_index"):
            if key not in v:
                raise ValueError(f"Scenario requires {key}")
        if not isinstance(v["choices"], list) or len(v["choices"]) < 2:
            raise ValueError("Scenario requires at least 2 choices")
        for c in v["choices"]:
            if not isinstance(c, dict) or "label" not in c or "outcome" not in c:
                raise ValueError("Each scenario choice requires label and outcome")
        if not (0 <= v["correct_index"] < len(v["choices"])):
            raise ValueError("Invalid correct_index — must be within choices range")
    elif lesson_type == "video":
        source = v.get("video_source", "youtube")
        if source == "hosted":
            if not isinstance(v.get("video_url"), str) or not v["video_url"]:
                raise ValueError("hosted video lessons require a non-empty video_url")
        else:
            if not isinstance(v.get("youtube_id"), str) or not v["youtube_id"]:
                raise ValueError("video lessons require a non-empty youtube_id")


class LessonCreate(BaseModel):
    type: Literal["card", "quiz", "scenario", "video"]
    content_json: dict
    xp_reward: int
    order_index: int
    apply_mission: ApplyMissionIn | None = None

    @field_validator("content_json")
    @classmethod
    def validate_content(cls, v: dict, info) -> dict:
        validate_lesson_content_json(info.data.get("type"), v)
        return v


class LessonUpdate(BaseModel):
    type: Literal["card", "quiz", "scenario", "video"] | None = None
    content_json: dict | None = None
    xp_reward: int | None = None
    apply_mission: ApplyMissionIn | None = None


class LessonOut(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID
    type: str
    content_json: dict
    xp_reward: int
    order_index: int
    apply_mission: ApplyMissionOut | None = None

    model_config = ConfigDict(from_attributes=True)


class GenerateLessonsRequest(BaseModel):
    concept: str = Field(min_length=1, max_length=200)
    count: int = Field(ge=1, le=8)
    types: list[Literal["card", "quiz", "scenario"]] = Field(min_length=1)


class LessonDraftOut(BaseModel):
    id: uuid.UUID
    level_id: uuid.UUID
    type: str
    content_json: dict
    concept: str
    moderation_safe: bool
    moderation_category: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerateLessonsResponse(BaseModel):
    created: list[LessonDraftOut]
    skipped: int


class LessonDraftUpdate(BaseModel):
    content_json: dict


# ── Video presign ───────────────────────────────────────────────────
class VideoPresignRequest(BaseModel):
    filename: str = Field(max_length=255)
    content_type: str
    size_bytes: int

    @field_validator("content_type")
    @classmethod
    def only_mp4(cls, v):
        if v != "video/mp4":
            raise ValueError("only video/mp4 is supported")
        return v


class VideoPresignResponse(BaseModel):
    asset_id: uuid.UUID
    key: str
    upload_url: str
    public_url: str


# ── Badge ───────────────────────────────────────────────────────────
class BadgeCreate(BaseModel):
    name: str
    description: str
    icon_url: str
    condition_type: Literal["lesson_count", "streak_days", "module_complete", "xp_total"]
    condition_value: int


class BadgeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon_url: str | None = None
    condition_type: Literal["lesson_count", "streak_days", "module_complete", "xp_total"] | None = None
    condition_value: int | None = None


class BadgeOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    icon_url: str
    condition_type: str
    condition_value: int

    model_config = ConfigDict(from_attributes=True)


# ── Challenge ───────────────────────────────────────────────────────
class ChallengeCreate(BaseModel):
    title: str
    description: str
    type: Literal["lessons_completed", "xp_earned", "streak"]
    target_value: int
    xp_reward: int
    badge_id: uuid.UUID | None = None
    starts_at: datetime
    ends_at: datetime
    is_premium: bool = False


class ChallengeUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    type: Literal["lessons_completed", "xp_earned", "streak"] | None = None
    target_value: int | None = None
    xp_reward: int | None = None
    badge_id: uuid.UUID | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_premium: bool | None = None


class ChallengeOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    type: str
    target_value: int
    xp_reward: int
    badge_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    is_premium: bool

    model_config = ConfigDict(from_attributes=True)


# ── Reorder ─────────────────────────────────────────────────────────
class ReorderItem(BaseModel):
    id: uuid.UUID
    order_index: int


class ReorderRequest(BaseModel):
    order: list[ReorderItem]


# ── Level ────────────────────────────────────────────────────────────
class AdminLevelCreate(BaseModel):
    title: str
    order_index: int
    is_premium: bool = False
    pass_threshold: float = 0.7
    icon: str = "📊"


class AdminLevelUpdate(BaseModel):
    title: str | None = None
    order_index: int | None = None
    is_premium: bool | None = None
    pass_threshold: float | None = None
    icon: str | None = None
    learning_objectives: list[NonEmptyStr] | None = None


class AdminLevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    order_index: int
    is_premium: bool
    pass_threshold: float
    content_source: str
    icon: str
    lesson_count: int = 0
    learning_objectives: list[str] | None = None


# ── Settings ────────────────────────────────────────────────────────
class AdminSettingsOut(BaseModel):
    alert_emails: list[str]
    starting_cash: dict[str, str] = {}


class AdminSettingsUpdate(BaseModel):
    alert_emails: list[EmailStr]
    starting_cash: dict[str, str] | None = None

    @field_validator("alert_emails")
    @classmethod
    def _clean(cls, v: list) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for e in v:
            s = str(e).strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
        if len(out) > 10:
            raise ValueError("at most 10 alert emails")
        return out


# ── Engagement ───────────────────────────────────────────────────────
class LessonEngagementOut(BaseModel):
    lesson_id: uuid.UUID
    type: str
    label: str
    order: int
    views: int
    completions: int
    completion_rate: float | None
    average_score: float | None
    drop_off: int

    model_config = ConfigDict(from_attributes=True)


class ModuleEngagementOut(BaseModel):
    module_id: uuid.UUID
    learners_started: int
    learners_completed: int
    completion_rate: float | None
    average_score: float | None
    lessons: list[LessonEngagementOut]

    model_config = ConfigDict(from_attributes=True)


# ── Video health ────────────────────────────────────────────────────
class VideoHealthItem(BaseModel):
    lesson_id: uuid.UUID
    module_id: uuid.UUID
    module_title: str
    lesson_title: str
    youtube_id: str
    status: str | None  # ok | dead | unknown | None (never checked)
    http_status: int | None
    checked_at: datetime | None

    model_config = {"from_attributes": True}


class VideoHealthCheckResult(BaseModel):
    summary: dict
    items: list[VideoHealthItem]
