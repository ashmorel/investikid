# Tiered Lesson Depth (10 / 15 / 20) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate richer levels — tier 1 → 10, tier 2 → 15, tier 3 → 20 lessons — via a teach-card + practice-quiz pair per concept.

**Architecture:** A `LESSONS_PER_TIER` map drives an exact per-level target. `generate_native_level_lessons` round-robins `(concept, ["card","quiz"])` and stops at the target (instead of one lesson per concept). The curriculum designer is told to emit ~`ceil(target/2)` concepts per level, and its output token budget is raised so the larger tree doesn't truncate.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async; the authoring (Opus) LLM tier; pytest.

## Global Constraints
- Spec: `docs/superpowers/specs/2026-06-21-lesson-depth-tiered-design.md`.
- Branch `main` (beta straight-to-main). End commits with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Engine change ONLY — no migration. Applying to live GB content is a later operator run (re-design → regenerate → review → approve-replace).
- Lesson types stay `card` + `quiz` (no new types). Concision rules unchanged (per-lesson).
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `db_session`. Verify: `/Users/leeashmore/Local Repo/.venv/bin/pytest` + `ruff check .` from `backend/`.

---

### Task 1: Tiered target + exact-count generator

**Files:**
- Modify: `backend/app/services/admin_content_generation_service.py`
- Test: `backend/tests/test_lesson_depth.py`

**Interfaces:**
- Produces: `LESSONS_PER_TIER: dict[int,int]`; `target_lessons_for_tier(tier: int | None) -> int`; `generate_native_level_lessons(...)` now creates exactly `target_lessons_for_tier(complexity_tier)` lessons.

- [ ] **Step 1: Add the config + helper** near the top of `admin_content_generation_service.py` (after `_SCHEMA_HINT`):
```python
# Lessons generated per level, by complexity tier (1 foundational … 3 advanced).
# lessons = target; each concept yields a teach-card + practice-quiz pair.
LESSONS_PER_TIER: dict[int, int] = {1: 10, 2: 15, 3: 20}


def target_lessons_for_tier(tier: int | None) -> int:
    return LESSONS_PER_TIER.get(tier or 0, LESSONS_PER_TIER[2])
```

- [ ] **Step 2: Write the failing tests** in `test_lesson_depth.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.admin_content_generation_service import (
    target_lessons_for_tier, generate_native_level_lessons,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_target_per_tier():
    assert target_lessons_for_tier(1) == 10
    assert target_lessons_for_tier(2) == 15
    assert target_lessons_for_tier(3) == 20
    assert target_lessons_for_tier(None) == 15  # fallback


async def test_generates_exact_target_alternating_types(db_session):
    from app.models.content import Module, Level
    from app.models.market_brief import MarketBrief
    mod = Module(topic="t", title="M", country_codes=[], market_code="GB",
                 is_premium=False, order_index=0, icon="📚", published=False)
    db_session.add(mod); await db_session.flush()
    lvl = Level(module_id=mod.id, title="L", order_index=0, is_premium=False,
                pass_threshold=0.7, learning_objectives=["o"])
    db_session.add(lvl); await db_session.flush()
    brief = MarketBrief(market_code="GB", brief_json={"currency": "GBP"}, status="verified")
    db_session.add(brief); await db_session.flush()

    calls = []
    async def fake_one(session, *, level, module, concept, lesson_type, **kw):
        calls.append((concept, lesson_type))
        return object()  # stand-in draft; non-None counts as created
    with patch("app.services.admin_content_generation_service._generate_one",
               side_effect=fake_one):
        result = await generate_native_level_lessons(
            db_session, lvl, brief=brief,
            concepts=[f"c{i}" for i in range(10)], complexity_tier=3,
        )
    assert len(calls) == 20                       # tier 3 → exactly 20
    assert calls[0] == ("c0", "card")
    assert calls[1] == ("c0", "quiz")             # teach + practice per concept
    assert len(result.created) == 20
```

- [ ] **Step 3: Run → fail.** `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_lesson_depth.py -v`.

- [ ] **Step 4: Rewrite the generator loop** in `generate_native_level_lessons` (replace the `for i, concept in enumerate(concepts)` body) so it emits exactly `target` lessons by round-robin over `(concept, type)` pairs:
```python
    module = await session.get(Module, level.module_id)
    type_cycle = types or ["card", "quiz"]
    target = target_lessons_for_tier(complexity_tier)
    result = GenerationResult()
    if not concepts:
        await session.commit()
        return result
    n_types = len(type_cycle)
    for n in range(target):
        concept = concepts[(n // n_types) % len(concepts)]
        lesson_type = type_cycle[n % n_types]
        draft = await _generate_one(
            session, level=level, module=module, concept=concept,
            lesson_type=lesson_type, brief=brief.brief_json,
            source_text=None, complexity_tier=complexity_tier,
        )
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
    await session.commit()
    return result
```
Iteration order: index `n` → `card` when `n` even, `quiz` when odd; concept advances every `n_types` lessons (`c0,c0,c1,c1,…`), wrapping `% len(concepts)` if a level returned fewer concepts than `ceil(target/2)`.

- [ ] **Step 5: Run → pass.** `pytest tests/test_lesson_depth.py -v`.

- [ ] **Step 6: Update the existing native-batch regression** if it asserts a specific lesson count. Run `pytest tests/test_curriculum_native_batch.py -v`; if a test seeded N concepts and expected N created, update it to expect `target_lessons_for_tier(tier)` (the test's level tier). `ruff check .`.

- [ ] **Step 7: Commit.**
```bash
git add backend/app/services/admin_content_generation_service.py backend/tests/test_lesson_depth.py backend/tests/test_curriculum_native_batch.py
git commit -m "feat(content-gen): tiered lesson depth (10/15/20) via card+quiz per concept"
```

---

### Task 2: Designer emits more concepts + larger token budget

**Files:**
- Modify: `backend/app/services/market_curriculum/designer.py`
- Test: `backend/tests/test_curriculum_designer.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: designer prompt instructs per-tier concept counts; designer LLM call uses a larger `max_tokens`.

- [ ] **Step 1: Write the failing test** in `test_curriculum_designer.py` (assert the prompt carries the per-tier concept-count instruction):
```python
def test_prompt_requests_tiered_concept_counts():
    from app.services.market_curriculum.designer import _build_prompt  # or the prompt fn used
    prompt = _build_prompt(market_code="GB", brief_json={"currency": "GBP"})
    assert "5 concepts" in prompt and "8 concepts" in prompt and "10 concepts" in prompt
```
(Check `designer.py` for the actual prompt-builder name/signature and adapt the call; if the prompt is built inline in `design_curriculum`, extract a `_build_prompt` helper as part of this task so it's unit-testable.)

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Add the concept-count instruction** to the designer prompt (near the existing SPIRAL / complexity_tier instructions, ~designer.py:28-30):
```python
        f"CONCEPT COUNT per level scales with tier so lessons deepen: a tier-1 level "
        f"has 5 concepts, a tier-2 level 8 concepts, a tier-3 level 10 concepts. Each "
        f"concept is a distinct sub-idea (no near-duplicates); we expand each into a "
        f"teaching card + a practice question.\n\n"
```

- [ ] **Step 4: Raise the designer token budget.** Find the `client.complete(... max_tokens=4000 ...)` call in `design_curriculum` and raise it so the larger tree isn't truncated:
```python
            max_tokens=16000,
```
(Authoring tier = Opus, which supports this. Leave a code comment: larger tree — 9 modules × up to 10 concepts/level — needs headroom.)

- [ ] **Step 5: Run → pass.** `pytest tests/test_curriculum_designer.py -v && ruff check .`.

- [ ] **Step 6: Commit.**
```bash
git add backend/app/services/market_curriculum/designer.py backend/tests/test_curriculum_designer.py
git commit -m "feat(curriculum): designer emits tiered concept counts (5/8/10) + larger token budget"
```

---

### Final verification
- [ ] `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q && ruff check .`
- [ ] Push to `main`; CI green (backend-only — frontend jobs skip via path filter).
- [ ] **Operator (post-deploy, manual):** in admin Market Content → GB → re-Design the curriculum → Generate all (Opus authoring) → spot-check a tier-3 level has ~20 lessons (card/quiz mix, not filler) → review → approve-replace. Watch generation cost (≈45 lessons/module now).
