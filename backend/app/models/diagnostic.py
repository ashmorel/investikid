import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DiagnosticItem(Base):
    """A single calibrated diagnostic question for the A2 assessment engine.

    Used to measure a child's mastery before and after a learning unit.
    Items are tagged with a market, topic, and optional concept (FK), and
    carry telemetry counters (times_shown, times_correct) for adaptive
    difficulty calibration.

    difficulty_tier: 1 = beginner, 2 = intermediate, 3 = advanced.
    status: draft → approved → retired (approved items surface to learners).
    source: generated (LLM-authored) or authored (human-written).
    """

    __tablename__ = "diagnostic_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    market_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(30), nullable=False)
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        # FK defined in migration; relationship navigates it here
    )
    # difficulty_tier: 1 = beginner, 2 = intermediate, 3 = advanced
    difficulty_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list] = mapped_column(JSON, nullable=False)
    answer_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    # status values: draft / approved / retired
    status: Mapped[str] = mapped_column(
        String(12), nullable=False, default="draft", index=True
    )
    # source values: generated / authored
    source: Mapped[str] = mapped_column(String(12), nullable=False)
    times_shown: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    times_correct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default="now()",
        nullable=False,
    )

    # Relationship to Concept (nullable; concept row may be deleted)
    concept: Mapped["Concept | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Concept",
        foreign_keys=[concept_id],
        primaryjoin="DiagnosticItem.concept_id == Concept.id",
        lazy="select",
    )
