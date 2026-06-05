import pytest

from app.models.content import Lesson, Level, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_video(db_session, youtube_id):
    m = Module(topic="savings", title="Cron Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=10,
                    content_json={"youtube_id": youtube_id, "caption": "Intro"})
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def test_run_emails_only_when_dead(db_session, monkeypatch):
    await _seed_video(db_session, "deadID")

    sent: list[dict] = []

    async def fake_alert(session, headline, detail):
        sent.append({"headline": headline, "detail": detail})

    from app.video_health import run as cron

    async def fake_check(session, *, client=None):
        return {"ok": 0, "dead": 1, "unknown": 0,
                "dead_items": [{"lesson_id": "x", "youtube_id": "deadID",
                                "module_title": "Cron Mod", "lesson_title": "Intro"}]}
    monkeypatch.setattr(cron, "check_all_videos", fake_check)
    monkeypatch.setattr(cron, "send_video_alert", fake_alert)

    await cron.run(db_session)
    assert len(sent) == 1 and "deadID" in sent[0]["detail"]


async def test_run_no_email_when_all_ok(db_session, monkeypatch):
    sent: list[dict] = []
    from app.video_health import run as cron

    async def fake_check(session, *, client=None):
        return {"ok": 2, "dead": 0, "unknown": 1, "dead_items": []}

    async def fake_alert(session, headline, detail):
        sent.append({"headline": headline})

    monkeypatch.setattr(cron, "check_all_videos", fake_check)
    monkeypatch.setattr(cron, "send_video_alert", fake_alert)
    await cron.run(db_session)
    assert sent == []
