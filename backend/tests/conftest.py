from datetime import date

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_session
from app.main import app
from app.routers.simulator import get_price_provider
from app.services.price_provider import StaticPriceProvider

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


@pytest_asyncio.fixture(scope="session", autouse=True)
async def seed_markets_once(engine):
    """Seed the market catalog once per test session.

    Market rows must exist before any User or Module can be inserted (FK).
    Session-scoped so it runs once and persists for the lifetime of the test DB.
    """
    from app.seed.markets import seed_markets

    async with engine.begin() as conn:
        session = AsyncSession(bind=conn, expire_on_commit=False)
        await seed_markets(session)
        await session.commit()
        await session.close()


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
async def admin_client(client, db_session):
    """Authenticated admin session: registers + logs in a user, flags it is_admin.

    Mirrors test_content._register_and_login (register + login set the
    access_token + csrf_token cookies on the client), then copies the csrf
    cookie into the X-CSRF-Token header so admin mutations pass CSRF.
    """
    from sqlalchemy import select

    from app.models.user import User

    payload = {
        "email": "admin@example.com",
        "username": "adminuser",
        "password": "SecurePass123!",
        "dob": "2010-05-10",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    user = await db_session.scalar(
        select(User).where(User.username == "adminuser")
    )
    user.is_admin = True
    await db_session.flush()
    return client


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_price_provider] = lambda: StaticPriceProvider()
    try:
        app.state.limiter.reset()
    except Exception:
        pass
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
