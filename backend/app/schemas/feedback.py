from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

FeedbackType = Literal["bug", "feature", "general"]


class FeedbackCreate(BaseModel):
    feedback_type: FeedbackType
    message: str = Field(min_length=1, max_length=2000)
    page_url: str | None = Field(default=None, max_length=500)


class FeedbackCreateResponse(BaseModel):
    id: uuid.UUID


class FeedbackOut(BaseModel):
    id: uuid.UUID
    submitter: str
    submitter_role: str
    feedback_type: str
    message: str
    page_url: str | None
    created_at: datetime


class FeedbackListResponse(BaseModel):
    items: list[FeedbackOut]
    total: int
    page: int
    per_page: int
