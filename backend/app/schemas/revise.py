from __future__ import annotations

from pydantic import BaseModel


class ReviseQuestion(BaseModel):
    ref: str
    kind: str  # "weak" | "refresher"
    module_id: str
    lesson_id: str
    concept: str
    question: str
    choices: list[str]


class ReviseSession(BaseModel):
    items: list[ReviseQuestion]


class ReviseModule(BaseModel):
    module_id: str
    title: str
    icon: str
    topic: str
    due_weak_count: int


class ReviseAnswerIn(BaseModel):
    ref: str
    selected_index: int


class ReviseAnswerResult(BaseModel):
    correct: bool
    answer_index: int
    explanation: str
    xp_awarded: int
    goal_met: bool
