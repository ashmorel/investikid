# Level 2 & 3 Rollout — All Remaining Modules · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (or executing-plans). Steps use `- [ ]` checkboxes.

**Goal:** Give the 11 remaining single-level modules a Level 2 (free) and Level 3 (premium), matching the approved *What is a Stock?* pilot, by inlining validated `extra_levels` into `backend/app/seed/content.py`.

**Architecture:** The seed loop (`seed_modules_and_lessons`) is already generic — it iterates `spec.get("extra_levels", [])`, creating Level N at `order_index N` with `is_premium=premium_for_position(N)` (L2=idx1 free, L3=idx2 premium), `pass_threshold=0.7`, `content_source="authored"`, via the idempotent `_ensure_level_lessons`. **No seed-function change.** We only add data + tests.

**Tech Stack:** FastAPI · SQLAlchemy async · pytest (`loop_scope="session"`). Approved content lives in `docs/superpowers/specs/level-rollout-drafts/*.md` and the assembled spec `docs/superpowers/specs/2026-06-09-level-rollout-all-modules-design.md`.

**Spec:** `docs/superpowers/specs/2026-06-09-level-rollout-all-modules-design.md` (154 lessons, validated: 2 cards + 4 quizzes + 1 scenario per level; XP 10/25/20; quizzes have 4 choices; indices in range; first lesson a card; scenario after first quiz).

**Draft → seed module map (by topic+title):**

| Draft file | topic | title |
|---|---|---|
| savings__compound-interest.md | savings | Compound Interest Basics |
| budgeting__basics.md | budgeting | Budgeting Basics |
| budgeting__needs-vs-wants.md | budgeting | Needs vs Wants |
| risk__diversification.md | risk | Risk & Diversification |
| debt__credit.md | debt | Debt & Credit Explained |
| taxes__how-taxes-work.md | taxes | How Taxes Work |
| taxes__first-paycheque.md | taxes | Your First Paycheque |
| real-estate__reit.md | real_estate | What is a REIT? |
| entrepreneurship__side-hustle.md | entrepreneurship | Starting a Side Hustle |
| entrepreneurship__revenue-costs-profit.md | entrepreneurship | Revenue, Costs & Profit |
| crypto__what-is-crypto.md | crypto | What is Crypto? |

**Safety:** kids' app. Content was authored + reviewed for age-appropriateness; crypto extra-cautious; every scam/hype/risk scenario routes to a trusted grown-up. These lessons are **authored** seed content (not LLM-at-runtime), so no `moderate_output` path applies. The pilot's premium-gate model (#2) is unchanged.

**Verification (run from `backend/`):**
`/Users/leeashmore/Local Repo/.venv/bin/ruff check .` and `/Users/leeashmore/Local Repo/.venv/bin/pytest`.

**Commits:** branch `testing`; explicit `git add` of named paths only (never `-A`); leave the working-tree `.gitignore` + the 3 uncommitted iOS build files alone; messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. No promotion.

---

### Task 1: Inline the 11 modules' `extra_levels` (deterministic generator)

**Files:**
- Modify: `backend/app/seed/content.py` (insert `"extra_levels": [...]` into 11 module dicts)
- Source of truth: `docs/superpowers/specs/level-rollout-drafts/*.md` (validated literals)

Because 154 lessons are safety-relevant, do **not** retype them. Use a deterministic generator that (a) extracts each draft's validated `extra_levels` literal via bracket-matching + `ast.literal_eval`, (b) serialises it in the pilot's formatting (json.dumps with `ensure_ascii=False` for every string value, so £/emoji/quotes are correct), and (c) inserts the block into the matching module dict in `content.py` by brace-matching the dict and placing it immediately before the dict's closing `}` (after the `lessons` list). Modules are located by their unique `"topic": "X", "title": "Y",` line.

- [ ] **Step 1: Confirm baseline tests green**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_seed_content.py tests/test_stock_level_pilot.py -q`
Expected: PASS (pre-rollout state).

- [ ] **Step 2: Run the generator** (`/tmp/insert_extra_levels.py`, code in this repo's session) to insert all 11 blocks into `content.py`.

Expected: prints `inserted 11 modules`, content.py grows ~1500 lines, only insertions (no edits to existing lines).

- [ ] **Step 3: Syntax + lint check**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/python -c "import app.seed.content as c; print(sum(len(m.get('extra_levels',[])) for m in c._MODULES))"`
Expected: prints `24` (12 modules × 2 extra levels: stock + 11).
Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/seed/content.py`
Expected: PASS (no errors).

- [ ] **Step 4: Verify each rolled-out module parses to 2 extra levels of 7 lessons** with a one-off check:

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/python -c "import app.seed.content as c; [print(m['title'], [len(l['lessons']) for l in m.get('extra_levels',[])]) for m in c._MODULES]"`
Expected: every module prints `[7, 7]` (or stock `[7, 7]`); no module prints `[]`.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/app/seed/content.py
git commit -m "feat: add Level 2 (free) + Level 3 (premium) to all 11 remaining modules

Inlines validated extra_levels content (154 lessons) matching the
'What is a Stock?' pilot pattern. Seed loop already generic; data-only.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Rollout regression tests

**Files:**
- Create: `backend/tests/test_level_rollout.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.seed.content import _MODULES, seed_modules_and_lessons

_asyncio = pytest.mark.asyncio(loop_scope="session")

# The 11 modules rolled out in this change (topic, title), plus the pilot.
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
    """Covers stock + all 11: every extra-level lesson is well-formed."""
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
        assert [lv.is_premium for lv in levels] == [False, False, True], title
        for lv in levels[1:]:
            n = await db_session.scalar(
                select(func.count()).select_from(Lesson).where(Lesson.level_id == lv.id)
            )
            assert n == 7, (title, lv.title, n)
```

- [ ] **Step 2: Run — confirm fail before Task 1, pass after**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_level_rollout.py -q`
Expected: PASS (Task 1 already landed the data).

- [ ] **Step 3: Commit**

```bash
cd /Users/leeashmore/investikid
git add backend/tests/test_level_rollout.py
git commit -m "test: rollout coverage for all 11 modules' Level 2/3

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Full backend regression + push

- [ ] **Step 1: Ruff**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Expected: PASS.

- [ ] **Step 2: Full pytest**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
Expected: PASS (note any pre-existing environmental DB-hang per CLAUDE.md; rely on CI if so).

- [ ] **Step 3: Push and report CI**

```bash
cd /Users/leeashmore/investikid
git push origin testing
```
Then report CI status (path filters skip FE/a11y/responsive; backend job runs).

---

## Self-review

- **Spec coverage:** all 11 modules mapped + inlined (Task 1); shape/premium/idempotency covered (Task 2 + existing `test_seed_content.py` generic counter); pilot untouched.
- **No placeholders:** generator is deterministic from validated drafts; test code is complete.
- **Type consistency:** uses real fields (`order_index`, `is_premium`, `content_json`, `xp_reward`); `premium_for_position` unchanged.
- **No promotion / no FE change / no migration** (data-only seed change; new levels are created by the idempotent seeder on deploy).
