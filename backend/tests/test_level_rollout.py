import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.seed.content import _MODULES, seed_modules_and_lessons

_asyncio = pytest.mark.asyncio(loop_scope="session")

# The 11 modules rolled out in this change (topic, title).
ROLLOUT = [
    ("savings", "Compound Interest Basics"),
    ("budgeting", "Budgeting Basics"),
    ("budgeting", "Needs vs Wants"),
    ("risk", "Risk & Diversification"),
    ("debt", "Debt & Credit Explained"),
    ("taxes", "How Taxes Work"),
    ("taxes", "Your First Paycheque"),
    ("real_estate", "What is a REIT?"),
    ("entrepreneurship", "Starting a Side Hustle"),
    ("entrepreneurship", "Revenue, Costs & Profit"),
    ("crypto", "What is Crypto?"),
]


def test_all_rollout_modules_have_two_extra_levels_in_spec():
    for topic, title in ROLLOUT:
        spec = next(m for m in _MODULES if m["topic"] == topic and m["title"] == title)
        extra = spec.get("extra_levels", [])
        assert [lv["title"] for lv in extra] == ["Level 2", "Level 3"], (topic, title)
        for lv in extra:
            assert len(lv["lessons"]) == 7, (title, lv["title"])


def test_every_modules_extra_levels_content_is_sane():
    """Covers the pilot + all 11: every extra-level lesson is well-formed,
    opens with a card, and offers >= 5 quiz/scenario lessons."""
    for spec in _MODULES:
        for level in spec.get("extra_levels", []):
            qs = 0
            types = [le["type"] for le in level["lessons"]]
            assert types[0] == "card", (spec["title"], level["title"])
            for le in level["lessons"]:
                cj = le["content_json"]
                assert isinstance(le["xp_reward"], int)
                if le["type"] == "card":
                    assert cj["title"] and cj["body"]
                elif le["type"] == "quiz":
                    qs += 1
                    assert len(cj["choices"]) >= 2
                    assert 0 <= cj["answer_index"] < len(cj["choices"])
                    assert cj["question"] and cj["explanation"]
                elif le["type"] == "scenario":
                    qs += 1
                    assert cj["prompt"]
                    assert 0 <= cj["correct_index"] < len(cj["choices"])
                    assert all(c["label"] and c["outcome"] for c in cj["choices"])
                else:
                    raise AssertionError(f"bad type {le['type']} in {spec['title']!r}")
            assert qs >= 5, (spec["title"], level["title"], qs)


@_asyncio
async def test_rollout_modules_seed_three_levels_with_premium_l3(db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()
    for topic, title in ROLLOUT:
        module = await db_session.scalar(
            select(Module).where(Module.topic == topic, Module.title == title)
        )
        assert module is not None, (topic, title)
        levels = (await db_session.scalars(
            select(Level).where(Level.module_id == module.id).order_by(Level.order_index)
        )).all()
        assert [lv.order_index for lv in levels] == [0, 1, 2], title
        # L1 & L2 free, L3 premium (premium_for_position: order_index >= 2).
        assert [lv.is_premium for lv in levels] == [False, False, True], title
        for lv in levels[1:]:
            n = await db_session.scalar(
                select(func.count()).select_from(Lesson).where(Lesson.level_id == lv.id)
            )
            assert n == 7, (title, lv.title, n)
