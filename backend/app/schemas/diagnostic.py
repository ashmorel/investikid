"""Pydantic schemas for diagnostic assessment items."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

# Valid LLM tier values — shared between schemas and the router.
VALID_TIERS = frozenset({"lite", "standard", "premium"})


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
    # Verifier fields (NULL until the item has been verified)
    verifier_status: str | None = None
    verifier_answer_index: int | None = None
    verifier_note: str | None = None
    verified_at: datetime | None = None

    model_config = {"from_attributes": True}


class DiagnosticGenerateRequest(BaseModel):
    """Request body for the admin generate endpoint."""

    market_code: str
    topic: str
    difficulty_tier: Annotated[int, Field(ge=1, le=3)]
    count: Annotated[int, Field(ge=1, le=20)]


class DiagnosticItemPatch(BaseModel):
    """Editable fields for a diagnostic item (draft only)."""

    question: str | None = None
    choices: list[str] | None = None
    answer_index: int | None = None
    explanation: str | None = None
    difficulty_tier: Annotated[int | None, Field(ge=1, le=3)] = None
    concept_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _validate_choices_and_index(self) -> DiagnosticItemPatch:
        choices = self.choices
        answer_index = self.answer_index
        if choices is not None and len(choices) != 4:
            raise ValueError("choices must contain exactly 4 items")
        if answer_index is not None and not (0 <= answer_index <= 3):
            raise ValueError("answer_index must be in range 0-3")
        return self


class CoverageCell(BaseModel):
    """Coverage count for a single (topic, difficulty_tier) cell."""

    topic: str
    difficulty_tier: int
    approved_count: int


class DiagnosticListResponse(BaseModel):
    """Response for the filterable list endpoint."""

    items: list[DiagnosticItemRead]
    coverage: list[CoverageCell]


# ---------------------------------------------------------------------------
# Sweep (verify) endpoint schemas
# ---------------------------------------------------------------------------


class DiagnosticSweepRequest(BaseModel):
    """Request body for POST /admin/diagnostic-items/verify."""

    market_code: str | None = None
    topic: str | None = None
    status: str | None = None
    limit: Annotated[int, Field(ge=0, le=500)] = 50
    only_unverified: bool = False
    tier: Literal["lite", "standard", "premium"] = "premium"


class FlaggedItem(BaseModel):
    """Shape of a single flagged entry in the sweep response."""

    id: uuid.UUID
    topic: str
    difficulty_tier: int
    answer_index: int
    verifier_answer_index: int | None
    verifier_status: str
    verifier_note: str | None


class DiagnosticSweepResponse(BaseModel):
    """Response for POST /admin/diagnostic-items/verify."""

    verified: int
    agree: int
    mismatch: int
    ambiguous: int
    error: int
    flagged: list[FlaggedItem]
