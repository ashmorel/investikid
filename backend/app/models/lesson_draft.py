import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LessonDraft(Base):
    __tablename__ = "lesson_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("levels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    concept: Mapped[str] = mapped_column(String(200), nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    moderation_safe: Mapped[bool] = mapped_column(Boolean, nullable=False)
    moderation_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Slug emitted by the LLM during generation; resolved to concept_id at approval time.
    concept_slug: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
