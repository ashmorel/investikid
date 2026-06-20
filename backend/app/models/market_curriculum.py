import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketCurriculumProposal(Base):
    """A model-proposed, operator-reviewable curriculum tree for one market.
    At most one active (proposed/accepted) row per market; re-designing
    supersedes the prior active row."""

    __tablename__ = "market_curriculum_proposal"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="proposed")
    proposal_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    coverage_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
