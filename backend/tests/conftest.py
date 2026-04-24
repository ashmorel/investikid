import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_session
from app.main import app

_test_engine = None
_TestSession = None


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    global _test_engine, _TestSession
    import app.models  # noqa: F401 — registers all models
    _test_engine = create_async_engine(settings.test_database_url, echo=False)
    _TestSession = async_sessionmaker(_test_engine, expire_on_commit=False)
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    # Clean up before test to ensure isolation
    async with _TestSession() as clean_session:
        from sqlalchemy import delete, text
        from app.models.user import RefreshToken, UserProgress, User
        try:
            await clean_session.execute(delete(RefreshToken))
            await clean_session.execute(delete(UserProgress))
            await clean_session.execute(delete(User))
            await clean_session.commit()
        except Exception:
            await clean_session.rollback()

    async with _TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    # Reset rate-limiter state between tests so per-test rate limits are independent.
    try:
        app.state.limiter.reset()
    except Exception:
        pass
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
