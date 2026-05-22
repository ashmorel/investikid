from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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

    model_config = ConfigDict(from_attributes=True)


# ── Lesson ──────────────────────────────────────────────────────────
class LessonCreate(BaseModel):
    type: Literal["card", "quiz", "scenario"]
    content_json: dict
    xp_reward: int
    order_index: int

    @field_validator("content_json")
    @classmethod
    def validate_content(cls, v: dict, info) -> dict:
        lesson_type = info.data.get("type")
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
        return v


class LessonUpdate(BaseModel):
    type: Literal["card", "quiz", "scenario"] | None = None
    content_json: dict | None = None
    xp_reward: int | None = None


class LessonOut(BaseModel):
    id: uuid.UUID
    module_id: uuid.UUID
    type: str
    content_json: dict
    xp_reward: int
    order_index: int

    model_config = ConfigDict(from_attributes=True)


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
