from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.content import Lesson, LessonCompletion, Module
from app.models.gamification import Badge, UserBadge
from app.models.user import User, UserProgress
from app.services.analytics_service import _xp_to_next_level, build_child_analytics
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token


def _csrf_headers(client) -> dict:
    csrf = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": csrf} if csrf else {}


# ---------- unit: _xp_to_next_level ----------


class TestXpToNextLevel:
    """Unit tests for _xp_to_next_level (no async, no db)."""

    def test_xp_to_next_level_at_start(self):
        assert _xp_to_next_level(1, 0) == 100

    def test_xp_to_next_level_mid(self):
        assert _xp_to_next_level(2, 150) == 100  # need 250, have 150

    def test_xp_to_next_level_at_max(self):
        assert _xp_to_next_level(7, 9999) == 0


# ---------- integration: build_child_analytics (requires async) ----------

# Only apply asyncio mark to async tests below
asyncio_pytest_mark = pytest.mark.asyncio(loop_scope="session")


@asyncio_pytest_mark
async def test_analytics_empty_user(db_session):
    user = User(
        email="ana-empty@example.com", username="anaempty",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)

    assert result.level == 1
    assert result.xp == 0
    assert result.streak_count == 0
    assert result.lessons_completed == 0
    assert result.recent_lessons == []
    assert result.badges == []


@asyncio_pytest_mark
async def test_analytics_with_data(db_session):
    user = User(
        email="ana-full@example.com", username="anafull",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    progress = UserProgress(user_id=user.id, xp=480, level=3, streak_count=5)
    db_session.add(progress)

    module = Module(
        topic="stocks", title="Stocks 101",
        country_codes=["GB"], is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(module)
    await db_session.flush()

    lessons = []
    for i in range(3):
        lesson = Lesson(
            module_id=module.id, type="card", xp_reward=10, order_index=i,
            content_json={"title": f"Lesson {i}"},
        )
        db_session.add(lesson)
        lessons.append(lesson)
    await db_session.flush()

    for i, lesson in enumerate(lessons[:2]):
        db_session.add(LessonCompletion(
            user_id=user.id, lesson_id=lesson.id,
            completed_at=datetime.now(UTC) - timedelta(days=i),
            score=0.9 if i == 0 else None,
        ))

    badge = Badge(
        name="First Lesson", description="Complete your first lesson",
        icon_url="trophy", condition_type="lessons_completed", condition_value=1,
    )
    db_session.add(badge)
    await db_session.flush()
    db_session.add(UserBadge(user_id=user.id, badge_id=badge.id))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)

    assert result.level == 3
    assert result.xp == 480
    assert result.xp_to_next_level == 20
    assert result.streak_count == 5
    assert result.lessons_completed == 2
    assert len(result.recent_lessons) == 2
    assert result.recent_lessons[0].title == "Lesson 0"
    assert result.recent_lessons[0].score == 0.9
    assert len(result.badges) == 1
    assert result.badges[0].name == "First Lesson"


@asyncio_pytest_mark
async def test_recent_lessons_limited_to_5(db_session):
    user = User(
        email="ana-limit@example.com", username="analimit",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    module = Module(
        topic="budgeting", title="Budget",
        country_codes=["GB"], is_premium=False, order_index=1, icon="💰",
    )
    db_session.add(module)
    await db_session.flush()

    for i in range(8):
        lesson = Lesson(
            module_id=module.id, type="card", xp_reward=10, order_index=i,
            content_json={"title": f"Budget {i}"},
        )
        db_session.add(lesson)
        await db_session.flush()
        db_session.add(LessonCompletion(
            user_id=user.id, lesson_id=lesson.id,
            completed_at=datetime.now(UTC) - timedelta(hours=i),
        ))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)
    assert len(result.recent_lessons) == 5
    assert result.lessons_completed == 8


# ---------- endpoint: GET /parent/children includes analytics ----------

@asyncio_pytest_mark
async def test_children_endpoint_includes_analytics(client, db_session):
    await client.post("/auth/register", json={
        "email": "anakid@example.com", "username": "anakid", "password": "SecurePass123!",
        "dob": "2015-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "anaparent@example.com",
    })
    token = await issue_one_time_token(
        db_session, purpose=PARENT_MAGIC_AUDIENCE, email="anaparent@example.com",
        subject_id=None, expires_in=timedelta(minutes=15),
    )
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")

    r = await client.get("/parent/children")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    child = body[0]
    assert "analytics" in child
    ana = child["analytics"]
    assert ana["level"] == 1
    assert ana["xp"] == 0
    assert ana["streak_count"] == 0
    assert ana["lessons_completed"] == 0
    assert ana["recent_lessons"] == []
    assert ana["badges"] == []
    assert "xp_to_next_level" in ana
    assert "lessons_total" in ana


def test_child_analytics_out_has_modules_progress_default():
    from app.schemas.parent import ChildAnalyticsOut

    out = ChildAnalyticsOut(
        level=1, xp=0, xp_to_next_level=100, streak_count=0,
        lessons_completed=0, lessons_total=0, recent_lessons=[], badges=[],
    )
    assert out.modules_progress == []


def test_module_progress_out_nests_levels():
    import uuid as _uuid

    from app.schemas.parent import LevelProgressOut, ModuleProgressOut

    mod = ModuleProgressOut(
        module_id=_uuid.uuid4(), title="Stocks", icon="📈",
        lessons_completed=2, lessons_total=4,
        levels=[LevelProgressOut(
            level_id=_uuid.uuid4(), title="Level 1", state="in_progress",
            locked_reason=None, passed=False, lessons_completed=2, lessons_total=2,
        )],
    )
    assert mod.levels[0].state == "in_progress"
    assert mod.levels[0].locked_reason is None


@asyncio_pytest_mark
async def test_analytics_modules_progress_per_level(db_session):
    from app.models.content import Level

    user = User(
        email="ana-levels@example.com", username="analevels",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP", is_premium=False,
    )
    db_session.add(user)
    await db_session.flush()

    module = Module(topic="stocks", title="Stocks 101", country_codes=["GB"],
                    is_premium=False, order_index=0, icon="📈")
    db_session.add(module)
    await db_session.flush()
    l1 = Level(module_id=module.id, title="Level 1", order_index=0,
               is_premium=False, pass_threshold=0.7, icon="1️⃣")
    l2 = Level(module_id=module.id, title="Level 2", order_index=1,
               is_premium=True, pass_threshold=0.7, icon="2️⃣")
    db_session.add_all([l1, l2])
    await db_session.flush()

    lessons = {}
    for lv in (l1, l2):
        lessons[lv.id] = []
        for i in range(2):
            lsn = Lesson(module_id=module.id, level_id=lv.id, type="card",
                         xp_reward=10, order_index=i, content_json={"title": f"{lv.title}-{i}"})
            db_session.add(lsn)
            lessons[lv.id].append(lsn)
    await db_session.flush()
    for lsn in lessons[l1.id]:
        db_session.add(LessonCompletion(user_id=user.id, lesson_id=lsn.id, score=0.9))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)

    assert len(result.modules_progress) == 1
    mp = result.modules_progress[0]
    assert mp.title == "Stocks 101"
    assert mp.lessons_completed == 2
    assert mp.lessons_total == 4
    assert [lv.title for lv in mp.levels] == ["Level 1", "Level 2"]
    assert mp.levels[0].state == "completed"
    assert mp.levels[0].passed is True
    assert mp.levels[1].state == "locked"
    assert mp.levels[1].locked_reason == "premium"


@asyncio_pytest_mark
async def test_analytics_modules_progress_skips_unlevelled(db_session):
    user = User(
        email="ana-nolvl@example.com", username="ananolvl",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP", is_premium=False,
    )
    db_session.add(user)
    await db_session.flush()
    module = Module(topic="stocks", title="Legacy", country_codes=["GB"],
                    is_premium=False, order_index=0, icon="📈")
    db_session.add(module)
    await db_session.flush()
    db_session.add(Lesson(module_id=module.id, level_id=None, type="card",
                          xp_reward=10, order_index=0, content_json={"title": "x"}))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)
    assert result.modules_progress == []


@asyncio_pytest_mark
async def test_analytics_carries_standards_and_mastered_at(db_session):
    from app.models.content import Level, LevelMastery

    user = User(
        email="ana-cred@example.com", username="anacred",
        password_hash="x", dob=date(2012, 1, 1),
        country_code="GB", currency_code="GBP", is_premium=False,
    )
    db_session.add(user)
    await db_session.flush()

    standards = [{"framework": "Jump$tart", "code": "SI-1", "label": "Saving & Investing 1"}]
    module = Module(topic="stocks", title="Stocks Credible", country_codes=["GB"],
                    is_premium=False, order_index=0, icon="📈",
                    standards_alignment=standards)
    db_session.add(module)
    await db_session.flush()
    l1 = Level(module_id=module.id, title="Level 1", order_index=0,
               is_premium=False, pass_threshold=0.7, icon="1️⃣")
    db_session.add(l1)
    await db_session.flush()
    db_session.add(Lesson(module_id=module.id, level_id=l1.id, type="card",
                          xp_reward=10, order_index=0, content_json={"title": "x"}))
    await db_session.flush()
    mastered = datetime.now(UTC)
    db_session.add(LevelMastery(user_id=user.id, level_id=l1.id,
                                mastered_at=mastered, score=0.9))
    await db_session.flush()

    result = await build_child_analytics(db_session, user.id, user.country_code)

    mp = result.modules_progress[0]
    assert [s.model_dump() for s in mp.standards_alignment] == standards
    assert mp.levels[0].mastered_at is not None
