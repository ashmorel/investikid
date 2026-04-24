import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session


@pytest.mark.asyncio
async def test_session_is_async():
    async for session in get_session():
        assert isinstance(session, AsyncSession)
        break
