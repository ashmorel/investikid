from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ParentPreferences(Base):
    __tablename__ = "parent_preferences"

    parent_email: Mapped[str] = mapped_column(String(255), primary_key=True)
    trial_reminder_opt_out: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    weekly_digest_opt_out: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    last_digest_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
