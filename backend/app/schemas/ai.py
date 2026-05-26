import uuid
from datetime import datetime

from pydantic import BaseModel


class RecommendationOut(BaseModel):
    module_id: uuid.UUID
    score: float
    reason: str


class NextQuestOut(BaseModel):
    module_id: uuid.UUID
    lesson_id: uuid.UUID
    reason: str


class RecommendationsResponse(BaseModel):
    next_quest: NextQuestOut | None
    suggested_modules: list[RecommendationOut]


class PracticeRequest(BaseModel):
    wrong_answer_index: int | None = None


class PracticeResponse(BaseModel):
    question: str
    choices: list[str]
    answer_index: int
    explanation: str
    variant_rung: str | None = None


class TutorChatRequest(BaseModel):
    lesson_id: uuid.UUID
    message: str
    conversation_id: uuid.UUID | None = None


class TutorChatResponse(BaseModel):
    response: str
    conversation_id: uuid.UUID
    messages_remaining: int


class TopicMasteryOut(BaseModel):
    topic: str
    mastery_score: float
    quizzes_attempted: int
    quizzes_correct: int
    last_activity_at: str


class WeakConceptOut(BaseModel):
    topic: str
    concept: str
    times_wrong: int
    times_reinforced: int


class MasteryProfileResponse(BaseModel):
    topics: list[TopicMasteryOut]
    weak_concepts: list[WeakConceptOut]


class RecommendationCategoryItem(BaseModel):
    module_id: uuid.UUID
    lesson_id: uuid.UUID | None = None
    score: float
    reason: str
    review_prompt: str | None = None
    weak_concepts: list[str] = []


class ReviewSummary(BaseModel):
    due_count: int
    next_due_at: datetime | None = None


class CategorisedRecommendations(BaseModel):
    continue_learning: list[RecommendationCategoryItem]
    practise_again: list[RecommendationCategoryItem]
    something_new: list[RecommendationCategoryItem]
    review_summary: ReviewSummary


class TopicStrength(BaseModel):
    topic: str
    mastery_score: float
    status: str
    weak_count: int
    due_for_review: int
    total_concepts: int


class StrengthsAndGaps(BaseModel):
    topics: list[TopicStrength]
    overall_mastery: float


class CoachChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class CoachAction(BaseModel):
    type: str  # "lesson" | "module" | "review"
    module_id: str
    lesson_id: str | None = None
    label: str


class CoachChatResponse(BaseModel):
    response: str
    conversation_id: uuid.UUID
    messages_remaining: int
    actions: list[CoachAction]
