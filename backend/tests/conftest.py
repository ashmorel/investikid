from datetime import date

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_session
from app.main import app

settings.email_backend = "logging"


@pytest_asyncio.fixture(scope="session")
async def engine():
    import app.models  # noqa: F401 — registers all models

    eng = create_async_engine(settings.test_database_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    async with engine.connect() as conn:
        txn = await conn.begin()
        await conn.begin_nested()
        session = AsyncSession(bind=conn, expire_on_commit=False)

        @event.listens_for(session.sync_session, "after_transaction_end")
        def reopen_nested(s, transaction):
            if not conn.closed and not conn.invalidated and txn.is_active:
                if not s.in_nested_transaction():
                    s.begin_nested()

        yield session

        await session.close()
        if txn.is_active:
            await txn.rollback()


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
    try:
        app.state.limiter.reset()
    except Exception:
        pass
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
