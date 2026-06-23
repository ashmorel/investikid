import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ArcadeWord(Base):
    """Word bank for MoneyWord. Each entry is a finance term approved for daily puzzles."""

    __tablename__ = "arcade_words"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word: Mapped[str] = mapped_column(String(8), nullable=False)
    definition: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default="en", index=True)
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, server_default="pending", index=True)
    source: Mapped[str] = mapped_column(String(8), nullable=False)  # llm | manual
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("word", "language", name="uq_arcade_word_lang"),)


class ArcadeDailySchedule(Base):
    """One row per (puzzle_date, language) — maps a calendar day to a word."""

    __tablename__ = "arcade_daily_schedule"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    puzzle_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    word_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("arcade_words.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("puzzle_date", "language", name="uq_arcade_daily_date_lang"),)


class ArcadeDailyPlay(Base):
    """One row per (user_id, puzzle_date) — tracks a child's daily MoneyWord attempt."""

    __tablename__ = "arcade_daily_play"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    puzzle_date: Mapped[date] = mapped_column(Date, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    guesses: Mapped[list] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    solved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("user_id", "puzzle_date", name="uq_arcade_daily_play_user_date"),)
