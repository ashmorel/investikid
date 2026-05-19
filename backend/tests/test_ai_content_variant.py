import uuid
import datetime
import pytest

from app.models.content import Module, Lesson, LessonCompletion
from app.models.generated_content import GeneratedContent
from app.models.skill_profile import TopicMastery
from app.models.user import User
from app.services import ai_content_service
from app.services.ai_content_service import generate_practice_quiz

pytestmark = pytest.mark.asyncio(loop_scope="session")

_QUIZ = {"question": "What is saving?", "choices": ["A", "B", "C"],
         "answer_index": 0, "explanation": "Because."}


async def _setup(db_session, *, premium, profiling):
    m = Module(topic="savings", title="S", country_codes=[], is_premium=False, order_index=0, icon="🏦")
    db_session.add(m); await db_session.flush()
    lesson = Lesson(module_id=m.id, type="quiz",
                    content_json={"question": "q", "choices": ["A", "B"], "answer_index": 0},
                    xp_reward=10, order_index=0)
    db_session.add(lesson)
    u = User(username=f"u{uuid.uuid4().hex[:8]}", password_hash="x",
             dob=datetime.date(2014, 1, 1), country_code="GB", currency_code="GBP",
             is_premium=premium, profiling_enabled=profiling,
             email=f"{uuid.uuid4().hex[:8]}@e.com")
    db_session.add(u); await db_session.flush()
    return lesson, u


async def test_returns_variant_rung_and_caches_under_variant_key(db_session, monkeypatch):
    lesson, user = await _setup(db_session, premium=True, profiling=True)

    class FakeClient:
        async def complete(self, **kwargs):
            import json
            return json.dumps(_QUIZ)

    monkeypatch.setattr(ai_content_service, "get_llm_client", lambda **k: FakeClient())

    async def safe_mod(*a, **k):
        from app.services.moderation import ModerationResult
        return ModerationResult(safe=True, category=None, text="")

    monkeypatch.setattr(ai_content_service, "moderate_output", safe_mod)

    out = await generate_practice_quiz(
        db_session, lesson, user=user, topic="savings",
        concept="saving", premium=True,
    )
    assert out["variant_rung"] == "core"
    row = await db_session.scalar(
        GeneratedContent.__table__.select().where(
            GeneratedContent.lesson_id == lesson.id
        )
    )
    assert row is not None


async def test_cache_hit_is_variant_scoped(db_session, monkeypatch):
    lesson, user = await _setup(db_session, premium=True, profiling=True)
    from app.services.llm_client import get_model_name
    model = get_model_name("premium")
    db_session.add(GeneratedContent(
        lesson_id=lesson.id, concept="saving", model_used=model,
        variant_key="core:0", content_json=_QUIZ,
    ))
    await db_session.flush()

    calls = {"n": 0}

    class BoomClient:
        async def complete(self, **kwargs):
            calls["n"] += 1
            raise AssertionError("should not call LLM on cache hit")

    monkeypatch.setattr(ai_content_service, "get_llm_client", lambda **k: BoomClient())
    out = await generate_practice_quiz(
        db_session, lesson, user=user, topic="savings",
        concept="saving", premium=True,
    )
    assert out["question"] == _QUIZ["question"]
    assert out["variant_rung"] == "core"
    assert calls["n"] == 0


async def test_llm_failure_falls_back_to_random_cached_safe_variant(db_session, monkeypatch):
    lesson, user = await _setup(db_session, premium=True, profiling=True)
    from app.services.llm_client import get_model_name
    model = get_model_name("premium")
    db_session.add(GeneratedContent(
        lesson_id=lesson.id, concept="saving", model_used=model,
        variant_key="easier:0", content_json=_QUIZ,
    ))
    await db_session.flush()

    class FailClient:
        async def complete(self, **kwargs):
            from app.services.llm_client import LLMError
            raise LLMError("down")

    monkeypatch.setattr(ai_content_service, "get_llm_client", lambda **k: FailClient())
    out = await generate_practice_quiz(
        db_session, lesson, user=user, topic="savings",
        concept="saving", premium=True,
    )
    assert out["question"] == _QUIZ["question"]
