# AI-Authored Level 2/3 Pilot ("What is a Stock?") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a free **Level 2** and premium **Level 3** to the "What is a Stock?" module as version-controlled seed content, by extending the seeder to support multiple levels per module.

**Architecture:** Extract the seeder's lesson-insertion block into `_ensure_level_lessons(...)`; after Level 1, create/seed each module's optional `extra_levels` at `order_index` 1, 2, … with `is_premium=premium_for_position(i)`. The "What is a Stock?" module gets the two approved levels. Backend/seed-only — no migration, no FE change. Premium gate + module UX already shipped (#2, #1).

**Tech Stack:** SQLAlchemy async + the existing seeder; pytest.

**Conventions:** TDD. Explicit `git add <paths>` only — never `git add -A`; leave the unrelated `.gitignore` + iOS files alone. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Verify (from `backend/`): `/Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest`. No `cap sync`. Work on `testing`; do NOT promote.

**Verified facts:**
- `app/seed/content.py`: `_MODULES` is a list of dicts `{topic, title, country_codes, is_premium, order_index, icon, lessons:[...]}`. The "What is a Stock?" entry is `_MODULES[0]` (`topic="stocks", title="What is a Stock?"`). `seed_modules_and_lessons(session)` (l.804-865) is idempotent: matches module by topic+title, ensures a `Level` at `order_index 0` (`title="Level 1", is_premium=premium_for_position(0), pass_threshold=0.7, content_source="authored"`), then inserts missing lessons (identity via `_lesson_identity(type, content_json)`, slotted by `_insert_position([types], new_type)`, then normalises `order_index`). `premium_for_position` already imported (from #2).
- Lesson `content_json` shapes: `card {title, body}`; `quiz {question, choices:[str], answer_index:int, explanation}`; `scenario {prompt, choices:[{label, outcome}], correct_index:int}`. xp: card 10, quiz 25, scenario 20.
- Levels read path + premium gate unchanged (`content.py list_levels` → `derive_level_states`). #2 end-to-end gate test pattern lives in `tests/test_level_premium_model.py`.
- Approved content: `docs/superpowers/specs/2026-06-09-stock-module-level2-3-pilot-design.md` (verbatim Python below).

---

## File Structure
- **Modify** `backend/app/seed/content.py` — extract `_ensure_level_lessons`; add `extra_levels` loop; add `extra_levels` to the stock module spec (the L2/L3 content).
- **Create** `backend/tests/test_stock_level_pilot.py` — seed-result, idempotency, content-sanity, and premium-gate tests.

---

## Task 1: Extend the seeder for multiple levels + add the L2/L3 content

**Files:** Modify `backend/app/seed/content.py`; Create `backend/tests/test_stock_level_pilot.py`.

- [ ] **Step 1: Write the failing seed test** — Create `backend/tests/test_stock_level_pilot.py`. Use the project's seeded-DB / `db_session` fixture (grep `tests/` for how other seed tests get a session that has run `seed_modules_and_lessons`, e.g. a `seeded_session`/`db_session` fixture or call the seeder directly). Test:

```python
import pytest
from sqlalchemy import select
from app.models.content import Level, Lesson, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _stock_levels(session):
    module = await session.scalar(
        select(Module).where(Module.topic == "stocks", Module.title == "What is a Stock?")
    )
    assert module is not None
    levels = (await session.scalars(
        select(Level).where(Level.module_id == module.id).order_by(Level.order_index)
    )).all()
    return module, levels


async def test_stock_module_has_three_levels(db_session):
    _module, levels = await _stock_levels(db_session)
    assert [lv.order_index for lv in levels] == [0, 1, 2]
    assert [lv.is_premium for lv in levels] == [False, False, True]   # L1-2 free, L3 premium
    assert levels[1].title == "Level 2" and levels[2].title == "Level 3"
```

(Mirror the exact seeded-session fixture the repo uses. If tests run the seeder per-session, `db_session` already has it; otherwise call `await seed_modules_and_lessons(db_session)` in the test. Match existing seed tests.)

- [ ] **Step 2: Run to verify it fails** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_stock_level_pilot.py -q` → FAIL (only Level 1 today).

- [ ] **Step 3: Refactor the seeder** — in `app/seed/content.py`, extract the lesson-merge block (current l.842-864) into a module-level helper, then call it for Level 1 and each extra level:

```python
async def _ensure_level_lessons(session, module, level, lesson_specs):
    ordered = list((await session.scalars(
        select(Lesson).where(Lesson.level_id == level.id).order_by(Lesson.order_index)
    )).all())
    by_ident = {_lesson_identity(le.type, le.content_json): le for le in ordered}
    for lesson_spec in lesson_specs:
        ident = _lesson_identity(lesson_spec["type"], lesson_spec["content_json"])
        if ident in by_ident:
            continue
        new_lesson = Lesson(
            module_id=module.id, level_id=level.id,
            type=lesson_spec["type"], content_json=lesson_spec["content_json"],
            xp_reward=lesson_spec["xp_reward"], order_index=0,
        )
        session.add(new_lesson)
        by_ident[ident] = new_lesson
        pos = _insert_position([le.type for le in ordered], new_lesson.type)
        ordered.insert(pos, new_lesson)
    for i, le in enumerate(ordered):
        le.order_index = i
```

In `seed_modules_and_lessons`, replace the inline merge block with `await _ensure_level_lessons(session, module, level, spec["lessons"])`, then after it add:

```python
        for i, extra in enumerate(spec.get("extra_levels", []), start=1):
            lv = await session.scalar(
                select(Level).where(Level.module_id == module.id, Level.order_index == i)
            )
            if lv is None:
                lv = Level(
                    module_id=module.id, title=extra["title"], order_index=i,
                    is_premium=premium_for_position(i), pass_threshold=0.7,
                    content_source="authored",
                )
                session.add(lv)
                await session.flush()
            else:
                lv.title = extra["title"]
                lv.is_premium = premium_for_position(i)
            await _ensure_level_lessons(session, module, lv, extra["lessons"])
```

(Modules without `extra_levels` are unchanged.)

- [ ] **Step 4: Add the content** — add an `"extra_levels": [...]` key to the `_MODULES[0]` ("What is a Stock?") dict. Use this VERBATIM (copy exactly — it matches the approved spec + the content_json shapes):

```python
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Where stocks are bought and sold",
                    "body": "Stocks are traded on a stock exchange — a giant marketplace like the London Stock Exchange (LSE) or the New York Stock Exchange. Here's the surprise: when you buy a share, you're usually not buying it from the company. You're buying it from another investor who wants to sell theirs.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Every stock has a ticker",
                    "body": "A ticker is a short code that names a stock — like AAPL for Apple or TSLA for Tesla. Tickers make companies quick to find. Try searching one in the practice Simulator to see its price!",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "When you buy a share of a big company like Apple, who are you usually buying it from?",
                    "choices": ["The company itself, directly", "Another investor who wants to sell their share", "The government", "Your bank's savings team"],
                    "answer_index": 1,
                    "explanation": "Most of the time you trade with other investors on an exchange — not the company. The company only sold those shares once, long ago.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What is a stock exchange?",
                    "choices": ["A marketplace where shares are bought and sold", "A shop that only sells company products", "A savings account for grown-ups", "A type of dividend"],
                    "answer_index": 0,
                    "explanation": "An exchange (like the LSE or NYSE) is the marketplace where buyers and sellers trade shares.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "You hear about the 'FTSE 100' or 'S&P 500'. What is an index like that?",
                    "choices": ["A single company's share price", "A scoreboard that tracks many big companies at once", "A tax on investors", "A list of dividends"],
                    "answer_index": 1,
                    "explanation": "An index is like a scoreboard: it follows lots of companies together, so people can see how 'the market' is doing overall.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Company A is worth £1 trillion. Company B is worth £10 million. Which is the 'bigger' company by market value?",
                    "choices": ["Company A", "Company B", "They're exactly the same", "You can't tell from value"],
                    "answer_index": 0,
                    "explanation": "A company's total value is its 'market cap'. £1 trillion is far bigger than £10 million — Company A is the giant.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You're curious how a real company's share price moves, but you're brand new. What's the smartest first step?",
                    "choices": [
                        {"label": "Put your real birthday money straight into one stock", "outcome": "Risky — never invest real money you can't afford to lose, especially before you've learned the ropes."},
                        {"label": "Search its ticker in the practice Simulator and watch it with pretend money", "outcome": "Perfect — the Simulator lets you explore real prices and practise with zero risk before any real money is involved."},
                        {"label": "Buy whatever a video online tells you to", "outcome": "Be careful — lots of online 'tips' are hype or scams. Learn and practise first, and always ask a trusted grown-up."},
                    ],
                    "correct_index": 1,
                }},
            ]},
            {"title": "Level 3", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Don't put all your eggs in one basket",
                    "body": "If you put all your money into one company and it does badly, you could lose a lot. Spreading your money across many different companies is called diversification — if one struggles, the others can balance it out.",
                }},
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Time in the market beats timing the market",
                    "body": "Nobody — not even experts — can reliably guess the best day to buy or sell. Investors who stay invested for many years usually do better than those who jump in and out trying to be clever.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Which is generally LESS risky?",
                    "choices": ["Putting all your money in one company", "Spreading your money across many different companies", "They're equally risky", "Keeping it all as cash under your bed"],
                    "answer_index": 1,
                    "explanation": "Spreading out (diversifying) means one bad company won't sink everything. That's a core rule of smart investing.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "What is an index fund?",
                    "choices": ["A single risky company", "A basket that holds many companies at once, giving instant diversification", "A loan you take out to invest", "A type of bank fee"],
                    "answer_index": 1,
                    "explanation": "An index fund holds lots of companies together — buying one is like buying a whole scoreboard of businesses at once.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Trying to guess the perfect day to buy or sell is called 'timing the market'. Is it a reliable way to invest?",
                    "choices": ["Yes, anyone can do it easily", "No — even experts can't do it reliably, so staying invested long-term usually works better", "Yes, if you watch the news every hour", "Only on weekends"],
                    "answer_index": 1,
                    "explanation": "Short-term prices are unpredictable. Patience and time usually beat trying to guess the perfect moment.",
                }},
                {"type": "quiz", "xp_reward": 25, "content_json": {
                    "question": "Investments that could grow a lot usually also carry…",
                    "choices": ["More risk of falling in value", "A guarantee from the government", "No risk at all", "Free money"],
                    "answer_index": 0,
                    "explanation": "Higher possible reward almost always comes with higher risk. There's no reward with zero risk — that's the trade-off.",
                }},
                {"type": "scenario", "xp_reward": 20, "content_json": {
                    "prompt": "You have £100 of pretend money to invest for 10 years in the Simulator. What's the wisest approach?",
                    "choices": [
                        {"label": "Put all £100 into the one stock a friend is hyping", "outcome": "Too risky — if that single company struggles, your whole £100 is exposed. No diversification."},
                        {"label": "Spread it across several companies (or a fund) and leave it to grow", "outcome": "Wise — diversifying and giving it years to grow is exactly how patient investors lower risk and let compounding work."},
                        {"label": "Buy and sell every single day to chase quick wins", "outcome": "This is 'timing the market' — unreliable, stressful, and usually loses to just staying invested."},
                    ],
                    "correct_index": 1,
                }},
            ]},
        ],
```

- [ ] **Step 5: Extend the seed test with lesson counts** — add to the test: `len(L2.lessons)==7` and `len(L3.lessons)==7` (query `Lesson` by `level_id`; L2 has 2 cards+4 quizzes... — actually L2 = 2 cards + 4 quizzes + 1 scenario = 7; L3 = 2 cards + 4 quizzes + 1 scenario = 7). Assert each count `== 7` (or `>=` to be robust). Confirm the exact counts from the content above before asserting.

- [ ] **Step 6: Run** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_stock_level_pilot.py -q` → PASS. (If the seeded fixture is session-scoped and a DB hang occurs ~90s, it's the local Postgres — note it, rely on CI.)

- [ ] **Step 7: Lint + commit**

```bash
cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check app/seed/content.py tests/test_stock_level_pilot.py
cd /Users/leeashmore/investikid
git add backend/app/seed/content.py backend/tests/test_stock_level_pilot.py
git commit -m "$(cat <<'EOF'
feat(content): Level 2 (free) + Level 3 (premium) for "What is a Stock?"

Extend the seeder to support per-module extra_levels (idempotent), and add the
reviewed L2 "how the market works" + L3 "investing wisely" content. L3 is
premium via order_index>=2.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Content-sanity + end-to-end premium-gate tests

**Files:** Modify `backend/tests/test_stock_level_pilot.py`.

- [ ] **Step 1: Content-sanity unit test (no DB)** — import `_MODULES`; for the stock module's `extra_levels`, assert for every lesson:
  - `card` → non-empty `title` and `body`.
  - `quiz` → `choices` len ≥ 2, `0 <= answer_index < len(choices)`, non-empty `question` + `explanation`.
  - `scenario` → non-empty `prompt`, each choice has non-empty `label` + `outcome`, `0 <= correct_index < len(choices)`.

```python
def test_stock_extra_levels_content_sane():
    from app.seed.content import _MODULES
    stock = next(m for m in _MODULES if m["topic"] == "stocks" and m["title"] == "What is a Stock?")
    for level in stock["extra_levels"]:
        assert level["title"] in {"Level 2", "Level 3"}
        for lsn in level["lessons"]:
            cj = lsn["content_json"]
            if lsn["type"] == "card":
                assert cj["title"] and cj["body"]
            elif lsn["type"] == "quiz":
                assert len(cj["choices"]) >= 2
                assert 0 <= cj["answer_index"] < len(cj["choices"])
                assert cj["question"] and cj["explanation"]
            elif lsn["type"] == "scenario":
                assert cj["prompt"]
                assert all(c["label"] and c["outcome"] for c in cj["choices"])
                assert 0 <= cj["correct_index"] < len(cj["choices"])
            else:
                raise AssertionError(f"unexpected lesson type {lsn['type']}")
```

- [ ] **Step 2: Idempotency test** — run `seed_modules_and_lessons(db_session)` a second time (in a test, or assert the session fixture already represents a post-seed state and a re-run doesn't change counts): assert the stock module still has exactly 3 levels and the same per-level lesson counts after a second seed call. (Mirror how existing seed-idempotency tests, if any, are written.)

- [ ] **Step 3: End-to-end premium gate** — reuse the pattern from `tests/test_level_premium_model.py`: a **non-premium** child calling `GET /modules/{stock_id}/levels` sees the Level 3 entry with `is_premium True`, `locked_reason="premium"`; a **premium** child sees `locked_reason != "premium"`. (Get the stock module id from the seeded DB; reuse the premium/non-premium login helpers.)

- [ ] **Step 4: Run** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/pytest tests/test_stock_level_pilot.py -q` → PASS.

- [ ] **Step 5: Lint + commit**

```bash
cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check .
cd /Users/leeashmore/investikid
git add backend/tests/test_stock_level_pilot.py
git commit -m "$(cat <<'EOF'
test(content): sanity + idempotency + premium-gate for stock L2/L3 pilot

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Full regression + close-out

**Files:** none (verification only).

- [ ] **Step 1: Backend gate** — `cd backend && /Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest -q` (note any local-Postgres hang as environmental).
- [ ] **Step 2: Push + report** — `cd /Users/leeashmore/investikid && git push origin testing`; report CI status. Do NOT promote. Leave unrelated files alone. (On promotion the new levels appear after each env's seed runs on deploy.)

---

## Self-Review

**1. Spec coverage:** L2 (free) + L3 (premium) content → Task 1 (verbatim) ; seeder multi-level support → Task 1 refactor + `extra_levels` loop ; premium by position → `premium_for_position(i)` (i≥2) ; idempotency + sanity + e2e gate → Task 2 ; no migration / no FE → confirmed (seed-only). ✓

**2. Placeholder scan:** Full lesson content embedded verbatim; helper + loop code complete. The "mirror the seeded-session fixture / premium-login helpers" notes point at named existing files (`tests/test_level_premium_model.py`, existing seed tests). Confirm exact lesson counts (L2=7, L3=7) before asserting `==`. ✓

**3. Type consistency:** content_json shapes match the existing card/quiz/scenario contracts exactly; `_ensure_level_lessons(session, module, level, lesson_specs)` used identically for Level 1 and extras; `premium_for_position(i)` is the #2 helper. ✓
