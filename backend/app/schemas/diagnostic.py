"""Pydantic schemas for diagnostic assessment items."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DiagnosticItemRead(BaseModel):
    """Public read schema for a diagnostic item."""

    id: uuid.UUID
    market_code: str
    topic: str
    concept_id: uuid.UUID | None
    difficulty_tier: int
    question: str
    choices: list[str]
    answer_index: int
    explanation: str
    status: str
    source: str
    times_shown: int
    times_correct: int
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
