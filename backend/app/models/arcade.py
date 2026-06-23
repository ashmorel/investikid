import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ArcadeScore(Base):
    """One row per completed arcade play. Powers the weekly per-market leaderboard
    (sum/Top-N over a rolling window) and all-time personal bests (max)."""

    __tablename__ = "arcade_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # quiz_rush | moneyword
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    market_code: Mapped[str] = mapped_column(String(2), ForeignKey("markets.code"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
