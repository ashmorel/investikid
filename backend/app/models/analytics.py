import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalyticsEvent(Base):
    """First-party product-analytics event.

    Privacy contract (see docs/superpowers/specs/2026-06-12-product-analytics-design.md):
    pseudonymous user_id only (SET NULL on delete), no IP, no user-agent, no free text;
    props restricted to the allowlist in analytics_service. Read ONLY by
    analytics_service and the admin analytics endpoint — never by personalization.
    """

    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    age_tier: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_premium: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    props: Mapped[dict | None] = mapped_column(JSON, nullable=True)
