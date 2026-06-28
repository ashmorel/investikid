import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.concept import Concept


class TopicMastery(Base):
    __tablename__ = "topic_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "topic", name="uq_topic_mastery_user_topic"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    topic: Mapped[str] = mapped_column(String(30), primary_key=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quizzes_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quizzes_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class WeakConcept(Base):
    __tablename__ = "weak_concepts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(30), nullable=False)
    concept: Mapped[str] = mapped_column(String(200), nullable=False)
    market_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("markets.code"), nullable=False, default="GB", server_default="GB", index=True
    )
    concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    times_wrong: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    times_reinforced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    concept_ref: Mapped["Concept | None"] = relationship(
        "Concept", foreign_keys=[concept_id]
    )


class SpacedRepetitionItem(Base):
    __tablename__ = "spaced_repetition_items"
    __table_args__ = (
        UniqueConstraint("user_id", "weak_concept_id", name="uq_sr_user_concept"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weak_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("weak_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    repetition_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_review_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
