"""Pydantic schemas for the diagnostic session start endpoint (Task 2)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class DiagnosticItemPublic(BaseModel):
    """Item payload returned to the child — server-authoritative fields only.

    answer_index and explanation are intentionally excluded; they are never
    sent to the client.
    """

    id: uuid.UUID
    topic: str
    difficulty_tier: int
    question: str
    choices: list[str]

    model_config = {"from_attributes": True}


class DiagnosticStartResponse(BaseModel):
    """Response for POST /diagnostic/start."""

    session_id: uuid.UUID
    items: list[DiagnosticItemPublic]
