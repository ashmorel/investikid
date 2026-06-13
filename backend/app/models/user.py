import uuid
from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.services.age_tier import age_tier as _age_tier


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    topic_path: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content_region: Mapped[str | None] = mapped_column(String(2), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    biometric_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)
    parent_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    guardian_attested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", default=True
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_declined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    profiling_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    marketing_opt_in: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    policy_version_accepted: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    policy_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tier_override: Mapped[str | None] = mapped_column(String(16), nullable=True)

    @property
    def age_tier(self) -> str:
        """Live age tier: parent override if valid, else derived from dob."""
        if self.tier_override in ("explorer", "investor"):
            return self.tier_override
        return _age_tier(self.dob, date.today())

    progress: Mapped["UserProgress"] = relationship(
        "UserProgress", back_populates="user", uselist=False
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class UserProgress(Base):
    __tablename__ = "user_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    xp: Mapped[int] = mapped_column(default=0, nullable=False)
    level: Mapped[int] = mapped_column(default=1, nullable=False)
    streak_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    virtual_coins: Mapped[int] = mapped_column(default=0, nullable=False)
    streak_freezes: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    daily_goal_xp: Mapped[int] = mapped_column(default=30, server_default="30", nullable=False)
    xp_today: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    xp_today_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_push_sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sim_xp_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sim_xp_today: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="progress")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    jti: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
