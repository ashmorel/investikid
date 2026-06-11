import uuid
from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

LessonType = Literal["card", "quiz", "scenario", "video"]
ModuleTopic = Literal[
    "stocks", "savings", "real_estate", "budgeting", "risk",
    "crypto", "taxes", "debt", "entrepreneurship",
]

TOPIC_PATH_VALUES: frozenset[str] = frozenset(get_args(ModuleTopic))


class StandardRef(BaseModel):
    framework: str = Field(min_length=1)
    code: str = Field(min_length=1)
    label: str = Field(min_length=1)


class SourceRef(BaseModel):
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: ModuleTopic
    title: str
    country_codes: list[str]
    is_premium: bool
    order_index: int
    icon: str = "📚"
    locked: bool = False
    standards_alignment: list[StandardRef] | None = None
    sources: list[SourceRef] | None = None


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    type: LessonType
    content_json: dict
    xp_reward: int
    order_index: int
    completed: bool = False
    locked: bool = False


class LessonSummary(BaseModel):
    """Lightweight lesson entry for module listing — excludes content_json."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: LessonType
    title: str
    xp_reward: int
    order_index: int
    completed: bool = False


class LessonCompletionRequest(BaseModel):
    score: float | None = None  # 0.0–1.0 for quizzes, None for card/video


class LessonCompletionResult(BaseModel):
    xp_awarded: int
    already_completed: bool
    total_xp: int
    level: int
    streak_count: int
    streak_freezes: int = 0
    practice_available: bool = False


class LevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    order_index: int
    is_premium: bool
    icon: str = "📊"
    state: Literal["in_progress", "completed", "locked"]
    locked_reason: Literal["premium", "progression"] | None = None
    passed: bool = False
    lessons_total: int = 0
    lessons_completed: int = 0
    learning_objectives: list[str] | None = None
    mastered_at: datetime | None = None


class NextLessonOut(BaseModel):
    module_id: uuid.UUID
    module_title: str
    module_icon: str | None
    level_id: uuid.UUID
    lesson_id: uuid.UUID
    lesson_title: str
    mode: Literal["start", "continue"]


class NextLessonEnvelope(BaseModel):
    next: NextLessonOut | None
