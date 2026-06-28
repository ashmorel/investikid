import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Concept(Base):
    """A named, taxonomy concept within a topic.

    Topics are the 9 fixed domains (stocks, savings, real_estate, budgeting,
    risk, crypto, taxes, debt, entrepreneurship).  Each Concept belongs to
    exactly one topic, has a unique slug, a human-readable name, an optional
    short blurb, a difficulty tier (1–3) and an ordering index.
    """

    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    topic: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    blurb: Mapped[str | None] = mapped_column(String(400), nullable=True)
    difficulty_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
