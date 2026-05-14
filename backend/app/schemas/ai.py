import uuid

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
