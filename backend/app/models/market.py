from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Market(Base):
    """A country financial-education market (the 'money' axis). Content and users
    are scoped to a market. Keyed by ISO-3166 alpha-2 code to align with
    users.country_code / modules.country_codes."""
    __tablename__ = "markets"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    default_language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en")
    has_content: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
