import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict

LessonType = Literal["card", "quiz", "scenario", "video"]
ModuleTopic = Literal["stocks", "savings", "real_estate"]


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: ModuleTopic
    title: str
    country_codes: list[str]
    is_premium: bool
    order_index: int
    locked: bool = False


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
