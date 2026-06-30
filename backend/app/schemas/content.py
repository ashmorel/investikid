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
    # Free-form: per-market curricula (the curriculum engine) define their own
    # topics, so this is NOT constrained to the legacy ModuleTopic slug set —
    # constraining it makes /modules 500 on any market-native topic.
    topic: str
    title: str
    country_codes: list[str]
    is_premium: bool
    order_index: int
    icon: str = "📚"
    locked: bool = False
    standards_alignment: list[StandardRef] | None = None
    sources: list[SourceRef] | None = None
    machine_translated: bool = False


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
    machine_translated: bool = False


class LessonSummary(BaseModel):
    """Lightweight lesson entry for module listing — excludes content_json."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: LessonType
    title: str
    xp_reward: int
    order_index: int
    completed: bool = False
    machine_translated: bool = False


class LessonCompletionRequest(BaseModel):
    score: float | None = None  # 0.0–1.0 for quizzes, None for card/video


class RewardGrantOut(BaseModel):
    coins: int = 0
    badge_name: str | None = None
    badge_icon: str | None = None


class LessonCompletionResult(BaseModel):
    xp_awarded: int
    already_completed: bool
    total_xp: int
    level: int
    streak_count: int
    streak_freezes: int = 0
    freeze_used: bool = False  # True only when THIS completion consumed a freeze to save the streak
    practice_available: bool = False
    daily_goal_met: bool = False  # True only when THIS completion crossed the daily goal
    # Delight signals for the in-app-review prompt (B5) — only set on THIS completion:
    streak_milestone_reached: int | None = None  # the streak value when it just hit a multiple of 7
    level_mastered: bool = False  # True when this completion mastered a level for the first time
    reward: RewardGrantOut = RewardGrantOut()
    granted_collectables: list[str] = []


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


class OfflineBundleIds(BaseModel):
    """The full current id sets (as strings) the client evicts stale rows against."""
    modules: list[str] = []
    levels: list[str] = []
    lessons: list[str] = []


class OfflineBundleOut(BaseModel):
    """One-shot offline-sync snapshot for the user's active market.

    Reuses the exact `ModuleOut`/`LevelOut`/`LessonSummary`/`LessonOut` shapes the
    per-item content routes return so the device SQLite cache matches byte-for-byte.
    `lessons` is delta'd against `since`; the metadata maps + `current_ids` are
    always the full current set. `server_time` (DB clock, ISO8601) is the client's
    next `since`.
    """
    market: str
    server_time: str
    modules: list[ModuleOut]
    module_levels: dict[str, list[LevelOut]]
    level_lessons: dict[str, list[LessonSummary]]
    lessons: list[LessonOut]
    current_ids: OfflineBundleIds


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
