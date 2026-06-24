import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CosmeticItem(Base):
    __tablename__ = "cosmetic_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    emoji: Mapped[str] = mapped_column(String(8), nullable=False, server_default="🎁", default="🎁")
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    coin_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rarity: Mapped[str | None] = mapped_column(String(12), nullable=True)
    unlock_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unlock_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drop_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )


class UserCosmetic(Base):
    __tablename__ = "user_cosmetics"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cosmetic_items.id", ondelete="CASCADE"), primary_key=True
    )
    equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
