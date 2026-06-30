"""Pydantic schemas for the diagnostic session endpoints (Tasks 2–3)."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel


class DiagnosticStartRequest(BaseModel):
    """Body for POST /diagnostic/start.

    ``kind`` is validated server-side to the two allowed values so a client
    can never inject an arbitrary checkpoint kind. Optional/defaults to
    ``"baseline"`` so the onboarding (baseline) flow works without a body.
    """

    kind: Literal["baseline", "progress"] = "baseline"


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


# ---------------------------------------------------------------------------
# Task 3 — submit
# ---------------------------------------------------------------------------


class DiagnosticSubmitRequest(BaseModel):
    """Body for POST /diagnostic/submit."""

    session_id: uuid.UUID
    # item_id (str) → chosen answer index (int)
    answers: dict[str, int]
    # When True the child explicitly skipped the diagnostic; the session is
    # closed immediately with a kind="skipped" checkpoint (no scoring).
    skipped: bool = False


class CheckpointTopicOut(BaseModel):
    """Per-topic breakdown returned with the checkpoint summary."""

    topic: str
    correct: int
    attempted: int


class DiagnosticSubmitResponse(BaseModel):
    """Response for POST /diagnostic/submit — immutable checkpoint summary."""

    kind: str
    overall_score: float | None
    session_count: int
    topics: list[CheckpointTopicOut]
