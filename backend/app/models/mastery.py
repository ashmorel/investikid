import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.mastery import MasteryCheckpointTopic


class MasteryCheckpoint(Base):
    """Immutable mastery snapshot taken before or after a diagnostic session.

    kind: baseline (pre-unit), progress (post-unit), skipped (child skipped).
    overall_score: 0..1 fraction; None until the session is scored.
    session_count: number of diagnostic questions answered in this checkpoint.
    """

    __tablename__ = "mastery_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    market_code: Mapped[str] = mapped_column(String(8), nullable=False)
    # kind values: baseline / progress / skipped
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    session_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default="now()",
        nullable=False,
    )

    topics: Mapped[list["MasteryCheckpointTopic"]] = relationship(
        "MasteryCheckpointTopic",
        back_populates="checkpoint",
        cascade="all, delete-orphan",
        lazy="select",
    )


class MasteryCheckpointTopic(Base):
    """Per-topic breakdown for a single MasteryCheckpoint.

    correct / attempted counts drive the per-topic score displayed in the
    progress screen.  Deleted automatically when the parent checkpoint is
    removed (CASCADE).
    """

    __tablename__ = "mastery_checkpoint_topics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mastery_checkpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(30), nullable=False)
    correct: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted: Mapped[int] = mapped_column(Integer, nullable=False)

    checkpoint: Mapped["MasteryCheckpoint"] = relationship(
        "MasteryCheckpoint",
        back_populates="topics",
        foreign_keys=[checkpoint_id],
    )


class DiagnosticSession(Base):
    """Records a single diagnostic question-set presented to a child.

    item_ids: ordered list of DiagnosticItem UUIDs shown in this session.
    completed_at: None until the child finishes (or times out).
    """

    __tablename__ = "diagnostic_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    market_code: Mapped[str] = mapped_column(String(8), nullable=False)
    # kind values: baseline / progress / skipped
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    item_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default="now()",
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
