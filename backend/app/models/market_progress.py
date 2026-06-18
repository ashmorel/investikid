import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserMarketProgress(Base):
    """Per-market learning progress (XP). One row per (user, market). The row's
    existence means the user is enrolled in that market. Global engagement
    (streak/coins/goal/level/total-XP) stays on UserProgress."""

    __tablename__ = "user_market_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    market_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("markets.code"), primary_key=True
    )
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
