from datetime import date

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
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
        from sqlalchemy import delete

        from app.models.consent import OneTimeToken, SentEmail
        from app.models.content import Lesson, LessonCompletion, Module
        from app.models.gamification import Badge, Challenge, UserBadge, UserChallenge
        from app.models.generated_content import GeneratedContent
        from app.models.simulator import Holding, Portfolio, Trade
        from app.models.skill_profile import TopicMastery, WeakConcept
        from app.models.tutor import TutorConversation
        from app.models.user import RefreshToken, User, UserProgress
        try:
            await clean_session.execute(delete(OneTimeToken))
            await clean_session.execute(delete(SentEmail))
            await clean_session.execute(delete(Trade))
            await clean_session.execute(delete(Holding))
            await clean_session.execute(delete(Portfolio))
            await clean_session.execute(delete(RefreshToken))
            await clean_session.execute(delete(TutorConversation))
            await clean_session.execute(delete(GeneratedContent))
            await clean_session.execute(delete(LessonCompletion))
            await clean_session.execute(delete(Lesson))
            await clean_session.execute(delete(Module))
            await clean_session.execute(delete(UserBadge))
            await clean_session.execute(delete(UserChallenge))
            await clean_session.execute(delete(Badge))
            await clean_session.execute(delete(Challenge))
            await clean_session.execute(delete(WeakConcept))
            await clean_session.execute(delete(TopicMastery))
            await clean_session.execute(delete(UserProgress))
            await clean_session.execute(delete(User))
            await clean_session.commit()
        except Exception:
            await clean_session.rollback()

    async with _TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def user_with_module(db_session):
    """Shared fixture: creates a user, module, quiz lesson and card lesson for skill profile tests."""
    from app.models.content import Lesson, Module
    from app.models.user import User

    user = User(
        email="skill@example.com",
        username="skillkid",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    module = Module(
        topic="budgeting",
        title="Budgeting Basics",
        country_codes=[],
        is_premium=False,
        order_index=0,
        icon="💰",
    )
    db_session.add(module)
    await db_session.flush()

    quiz = Lesson(
        module_id=module.id,
        type="quiz",
        xp_reward=25,
        order_index=0,
        content_json={
            "question": "What is the 50/30/20 rule?",
            "choices": ["A", "B", "C"],
            "answer_index": 1,
            "explanation": "It splits income into needs, wants, savings.",
        },
    )
    card = Lesson(
        module_id=module.id,
        type="card",
        xp_reward=10,
        order_index=1,
        content_json={"title": "What is a budget?", "body": "A plan for your money."},
    )
    db_session.add_all([quiz, card])
    await db_session.flush()
    return user, module, quiz, card


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
