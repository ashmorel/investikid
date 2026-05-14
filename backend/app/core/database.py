from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


from sqlalchemy import event
from sqlalchemy.orm import Session as _SyncSession, with_loader_criteria

_soft_delete_installed = False


def _install_soft_delete_filter():
    global _soft_delete_installed
    if _soft_delete_installed:
        return
    _soft_delete_installed = True

    from app.models.user import User

    @event.listens_for(_SyncSession, "do_orm_execute")
    def _add_filtering_criteria(execute_state):
        if not execute_state.is_select:
            return
        if execute_state.execution_options.get("include_deleted"):
            return
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(User, User.deleted_at.is_(None), include_aliases=True)
        )


# Defer to avoid circular import when Alembic loads models before app.
# The app's create_app() or first session use will trigger it.
try:
    _install_soft_delete_filter()
except ImportError:
    pass
