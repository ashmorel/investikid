"""Pydantic schemas for the Concept taxonomy."""
from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

NonEmptyStr = Annotated[str, Field(min_length=1)]

VALID_TOPICS = frozenset({
    "stocks", "savings", "real_estate", "budgeting", "risk",
    "crypto", "taxes", "debt", "entrepreneurship",
})

VALID_TIERS = frozenset({1, 2, 3})


class ConceptIn(BaseModel):
    """Payload for creating or fully updating a Concept."""

    topic: str
    slug: NonEmptyStr = Field(max_length=60)
    name: NonEmptyStr = Field(max_length=120)
    blurb: str | None = Field(default=None, max_length=400)
    difficulty_tier: int = Field(ge=1, le=3)
    order_index: int = Field(ge=0)

    @field_validator("topic")
    @classmethod
    def _valid_topic(cls, v: str) -> str:
        if v not in VALID_TOPICS:
            raise ValueError(f"topic must be one of {sorted(VALID_TOPICS)!r}; got {v!r}")
        return v


class ConceptPatch(BaseModel):
    """Payload for a partial concept update (all fields optional)."""

    topic: str | None = None
    slug: str | None = Field(default=None, min_length=1, max_length=60)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    blurb: str | None = None
    difficulty_tier: int | None = Field(default=None, ge=1, le=3)
    order_index: int | None = Field(default=None, ge=0)

    @field_validator("topic")
    @classmethod
    def _valid_topic(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TOPICS:
            raise ValueError(f"topic must be one of {sorted(VALID_TOPICS)!r}; got {v!r}")
        return v


class ConceptOut(BaseModel):
    """Serialized concept, including aggregated counts."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: str
    slug: str
    name: str
    blurb: str | None
    difficulty_tier: int
    order_index: int
    lesson_count: int = 0


class TopicGroup(BaseModel):
    """All concepts for a single topic, plus the per-topic unmapped lesson count."""

    topic: str
    unmapped_count: int
    concepts: list[ConceptOut]


class LessonConceptPatch(BaseModel):
    """Set or clear a lesson's concept_id."""

    concept_id: uuid.UUID | None
