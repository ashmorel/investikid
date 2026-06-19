# Per-Market Content Waves Implementation Plan (Sub-project E2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a market-adaptation content pipeline — verified per-market brief → GB-scaffolded structure → market-grounded lesson generation (premium model, moderated) → human review/approve → per-market publish (`has_content`) — that makes any empty market completable, proven end-to-end on US drafts. Ships inert.

**Architecture:** Extends the existing premium-model draft generator (`admin_content_generation_service.py`, `LessonDraft`, the draft review/approve endpoints) to be market-aware, grounded in a new human-verified `MarketBrief`. Adds a GB→market scaffold and a per-market publish toggle. No new CMS; no change to GB content or serving.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres; React 18 + Vite + TS (admin UI). LLM via `get_llm_client("premium")`; safety via `moderate_output`.

**Spec:** `docs/superpowers/specs/2026-06-19-per-market-content-waves-design.md`
**Branch:** `testing`. Carries a prod DB migration → ask the snapshot question before prod.

---

## Existing pieces reused (do NOT rebuild)
- `admin_content_generation_service.py`: `_generate_one(session, *, level, module, concept, lesson_type)` (premium model + `validate_lesson_content_json` + `moderate_output` + `LessonDraft`), `_system_prompt(lesson_type, module, level)`, `generate_level_lessons(...)`.
- Admin endpoints (all under `Depends(get_current_admin)`, rate-limited): module/level/lesson CRUD; `POST /admin/levels/{id}/generate`; `GET /admin/levels/{id}/drafts`; `PUT /admin/lesson-drafts/{id}`; `POST /admin/lesson-drafts/{id}/approve` (→ real `Lesson`); `POST /admin/lesson-drafts/{id}/regenerate`.
- Content gating by `module.market_code` + `Market.has_content`. Alembic head: `d3f6a9c0b1e2`.

---

## File Structure
- Create `backend/app/models/market_brief.py`; migration `backend/alembic/versions/<rev>_market_briefs.py`.
- Create `backend/app/services/market_brief_service.py`; `backend/app/services/market_scaffold_service.py`.
- Modify `backend/app/services/admin_content_generation_service.py` (market-aware prompt + `generate_market_level_lessons`).
- Modify `backend/app/routers/admin.py` + `backend/app/schemas/admin.py` (brief, scaffold, generate-market, publish endpoints + schemas).
- Frontend: admin content UI extensions + `frontend/src/api/admin.ts` + `frontend/src/locales/en/admin.json`.
- Tests under `backend/tests/` and `frontend/src/**/__tests__/`.

---

### Task 1: `MarketBrief` model + migration

**Files:** Create `backend/app/models/market_brief.py`, `backend/alembic/versions/e4a7b2c1d0f3_market_briefs.py`; Modify `backend/app/models/__init__.py`; Test `backend/tests/test_market_brief_model.py`.

- [ ] **Step 1: Model**

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketBrief(Base):
    """Human-verified financial facts per market, grounding content generation."""
    __tablename__ = "market_briefs"

    market_code: Mapped[str] = mapped_column(String(2), ForeignKey("markets.code"), primary_key=True)
    brief_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="draft")  # draft|verified
    model_used: Mapped[str] = mapped_column(String(100), nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
```

Register in `backend/app/models/__init__.py` if models are imported there.

- [ ] **Step 2: Failing test** — `backend/tests/test_market_brief_model.py`: insert a `MarketBrief(market_code="US", brief_json={...}, status="draft")`, flush, re-fetch, assert fields. Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_market_brief_model.py -v` → FAIL.

- [ ] **Step 3: Migration** — confirm head `d3f6a9c0b1e2` (`cd backend && …/alembic heads`); verify `e4a7b2c1d0f3` free (`grep -rl …`). Create the revision (`down_revision="d3f6a9c0b1e2"`): `create_table("market_briefs", market_code PK String(2) FK markets.code, brief_json JSONB not null, status String(10) server_default 'draft', model_used String(100) server_default '', created_at/updated_at timestamptz server_default now())`; downgrade drops it. Use `postgresql.JSONB`.

- [ ] **Step 4: Apply + test** — `…/alembic upgrade head` then the test → PASS. Ruff. (Local DB hang → defer to CI.)

- [ ] **Step 5: Commit**
```bash
cd /Users/leeashmore/investikid && git add backend/app/models/market_brief.py backend/app/models/__init__.py backend/alembic/versions/e4a7b2c1d0f3_market_briefs.py backend/tests/test_market_brief_model.py && git commit -m "feat(market): MarketBrief model + migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Brief generation + verify (service + endpoints)

**Files:** Create `backend/app/services/market_brief_service.py`; Modify `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`; Test `backend/tests/test_market_brief.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_market_brief.py` (uses `admin_client`; mock the LLM where the service calls it):
  - `POST /admin/markets/US/brief/generate` (mock `get_llm_client` to return a JSON brief) → 200, status `draft`, brief_json has the expected keys.
  - `PUT /admin/markets/US/brief` edits brief_json → 200.
  - `POST /admin/markets/US/brief/verify` → status `verified`.
  - `require_verified_brief(session, "US")` returns the brief when verified; raises (or returns None) when draft/absent.
  Run → FAIL.

- [ ] **Step 2: Service** — `market_brief_service.py`:
```python
BRIEF_KEYS = ["currency", "tax_advantaged_accounts", "regulators", "deposit_protection", "typical_products", "local_examples", "notes"]


async def generate_brief(session, market):
    """Premium-model draft of the market's financial facts. Stored status=draft."""
    client = get_llm_client("premium")
    system = (
        f"You are a financial-education researcher. Produce a concise, FACTUAL brief of the "
        f"{market.name} ({market.code}) youth-finance landscape for curriculum writers. "
        f"Reply ONLY with JSON: {{currency, tax_advantaged_accounts:[...], regulators:[...], "
        f"deposit_protection, typical_products:[...], local_examples:[...], notes}}."
    )
    raw = await client.complete(system_prompt=system, messages=[{"role": "user", "content": f"Brief for {market.name}."}], temperature=0.3, max_tokens=900, response_format="json")
    parsed = json.loads(raw)  # tolerate failure → 502 in the endpoint
    # upsert MarketBrief(market_code=market.code, brief_json=parsed, status="draft", model_used=get_model_name("premium"))
    ...


async def require_verified_brief(session, market_code) -> MarketBrief:
    brief = await session.get(MarketBrief, market_code)
    if brief is None or brief.status != "verified":
        raise HTTPException(status.HTTP_409_CONFLICT, "market brief not verified")
    return brief
```
(Validate `parsed` is a dict; tolerate JSON errors → the endpoint returns 502. Mirror the `_generate_one` premium-client + `get_model_name` usage.)

- [ ] **Step 3: Schemas + endpoints** — add `MarketBriefOut`/`MarketBriefUpdate` to `schemas/admin.py`; in `admin.py` add (admin-gated, rate-limit generate): `POST /admin/markets/{code}/brief/generate`, `GET /admin/markets/{code}/brief`, `PUT /admin/markets/{code}/brief` (validate dict; set status back to `draft` on edit? — keep status, just update brief_json), `POST /admin/markets/{code}/brief/verify`. 404 if the market doesn't exist; 502 if generation returns invalid JSON.

- [ ] **Step 4: Run + ruff + commit**
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/market_brief_service.py backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_market_brief.py && git commit -m "feat(market): market brief generate/edit/verify pipeline

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Market-aware generation (the adaptation core)

**Files:** Modify `backend/app/services/admin_content_generation_service.py`, `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`; Test `backend/tests/test_market_content_generation.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_market_content_generation.py`: create a GB module+level+lesson and a US module+level (scaffolded-style, market_code=US) and a verified US `MarketBrief`. Mock `get_llm_client` with a spy. Call `generate_market_level_lessons(session, us_level, source_level=gb_level, brief=us_brief)` → asserts: a `LessonDraft` is created under `us_level`; the LLM `complete` was called with a system prompt that **includes brief facts (e.g. the currency) AND the GB source lesson text**; blocked (raises) when the brief is not verified. Run → FAIL.

- [ ] **Step 2: Extend the prompt + add the market generator** — in `admin_content_generation_service.py`:
  - Extend `_system_prompt` to accept optional `brief: dict | None = None` and `source_text: str | None = None`; when present, append a directive: *"Adapt the following GB lesson's concept into <market> using these verified facts: <brief>. Replace UK products/regulators/currency/examples (ISA→local tax-advantaged account, FCA→local regulator, £→local currency) with the market's real equivalents. Keep the learning objective, structure, and age level. Source lesson: <source_text>. Do not copy GB specifics."* Keep the existing schema-only behavior when both are None (so the existing generic generator is unchanged).
  - Add `generate_market_level_lessons(session, target_level, *, source_level, brief)`: for each GB `Lesson` under `source_level`, call a market-aware variant of `_generate_one` (passing `brief.brief_json` + the GB lesson's `_concat_text(content_json)` as `source_text`, and the GB lesson's `type` + a `concept` derived from its title/objective) → `LessonDraft` under `target_level`. Reuse `_generate_one`'s validate+moderate+store path (refactor `_generate_one` to optionally take `brief`/`source_text` and thread them into `_system_prompt`). Return a `GenerationResult`.
  - Guard: the caller passes a `verified` brief; the endpoint enforces it via `require_verified_brief`.

- [ ] **Step 3: Endpoint** — `POST /admin/levels/{level_id}/generate-market` (body `{ source_level_id }`): load target level + source level (404s) + `require_verified_brief(session, target_module.market_code)`; call `generate_market_level_lessons`; return the drafts (reuse `GenerateLessonsResponse`).

- [ ] **Step 4: Run + ruff** — new test + the existing `admin_content_generation` tests (regression: generic generation unchanged when brief/source are None) → PASS. Commit:
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/admin_content_generation_service.py backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_market_content_generation.py && git commit -m "feat(market): market-grounded lesson generation (brief + GB reference)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Scaffold a market from GB

**Files:** Create `backend/app/services/market_scaffold_service.py`; Modify `backend/app/routers/admin.py`; Test `backend/tests/test_market_scaffold.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_market_scaffold.py`: seed a couple of GB modules+levels; a verified US brief; mock the LLM (title/objective adaptation). Call `scaffold_market_from_gb(session, "US")` → asserts: US modules+levels created mirroring GB structure (same count, order, topic, icon, is_premium), `market_code="US"`, `has_content` still false, titles came from the (mocked) adapter; re-run is idempotent (no duplicates); raises if the brief isn't verified. Run → FAIL.

- [ ] **Step 2: Service** — `market_scaffold_service.py` `scaffold_market_from_gb(session, code)`:
  - `require_verified_brief(session, code)`.
  - If the market already has any module (`market_code==code`), return (idempotent).
  - For each GB `Module` (ordered): adapt `{title, conversation_prompt}` + each GB `Level`'s `{title, learning_objectives}` via a premium-model JSON call grounded in the brief (a small helper `_adapt_titles(client, brief, source)` returning the adapted strings; validate dict). Create new `Module` (market_code=code, copy topic/order_index/icon/is_premium/min_age/max_age/prerequisite structure; adapted title/prompt) and its `Level`s (copy order/is_premium/pass_threshold; adapted title/objectives). Do NOT create lessons.
  - Return a summary (counts).

- [ ] **Step 3: Endpoint** — `POST /admin/markets/{code}/scaffold` (admin-gated, rate-limited): 404 if market absent; calls the service; returns the summary.

- [ ] **Step 4: Run + ruff + commit**
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/market_scaffold_service.py backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_market_scaffold.py && git commit -m "feat(market): scaffold a market's module/level skeleton from GB

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Publish / unpublish a market

**Files:** Modify `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`; Test `backend/tests/test_market_publish.py`.

- [ ] **Step 1: Failing test** — `backend/tests/test_market_publish.py` (`admin_client`):
  - `POST /admin/markets/US/publish` with no US lessons → 409 (empty go-live guard); `Market.has_content` stays false.
  - Create a US module+level+approved `Lesson`; `POST /admin/markets/US/publish` → 200, `has_content` true.
  - `POST /admin/markets/US/unpublish` → `has_content` false; per-market progress rows untouched.
  Run → FAIL.

- [ ] **Step 2: Endpoints** — in `admin.py`:
```python
@router.post("/markets/{code}/publish")
async def publish_market(code: str, session: AsyncSession = Depends(get_session)):
    market = await session.get(Market, code)
    if market is None:
        raise HTTPException(404, "market not found")
    lesson_count = await session.scalar(
        select(func.count(Lesson.id)).select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id).where(Module.market_code == code)
    ) or 0
    if lesson_count == 0:
        raise HTTPException(409, "market has no lessons to publish")
    market.has_content = True
    await session.commit()
    return {"code": code, "has_content": True}
```
Plus `POST /markets/{code}/unpublish` (set `has_content=False`, commit). Both admin-gated.

- [ ] **Step 3: Run + ruff + commit**
```bash
cd /Users/leeashmore/investikid && git add backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_market_publish.py && git commit -m "feat(market): publish/unpublish a market (has_content, guarded)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Admin frontend — the market-content workflow

**Files:** Modify `frontend/src/api/admin.ts`, the admin content area (a new `MarketContent` admin page/section under `frontend/src/components/admin/`), `frontend/src/locales/en/admin.json`, admin routing; Test a focused component test.

- [ ] **Step 1: Failing test** — a component test for the new admin market-content panel: mock the admin API hooks; render; assert the workflow controls show (generate brief / verify / scaffold / publish) and a disabled→enabled gating (e.g. scaffold disabled until brief verified). Run → FAIL.

- [ ] **Step 2: API client** — in `frontend/src/api/admin.ts` add types + hooks for: brief generate/get/update/verify, scaffold, generate-market (per level), publish/unpublish. Mirror the existing admin API hook conventions.

- [ ] **Step 3: UI** — add a "Market content" admin section (a new component under `components/admin/`, routed in the admin layout/sidebar): pick a market → generate/edit/verify its brief → scaffold from GB → per-level "Generate (market)" feeding the EXISTING draft review/approve UI → publish/unpublish. Reuse existing draft-review components. All strings i18n'd (`admin` namespace). Keep it functional, not fancy. Gate controls on brief-verified / has-lessons as the backend does.

- [ ] **Step 4: Verify + commit** — `cd frontend && npx tsc -b && npm run lint && npx vitest run <the new test>` → clean + PASS; run existing admin tests for no regression.
```bash
cd /Users/leeashmore/investikid && git add frontend/src/api/admin.ts frontend/src/components/admin frontend/src/locales/en/admin.json frontend/src/pages && git commit -m "feat(market): admin market-content workflow UI (brief/scaffold/generate/publish)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(Adjust `git add` to the exact files changed.)

---

### Task 7: Full verification + promote

- [ ] **Step 1: Backend** — `cd backend && …/ruff check . && …/pytest -q`. All green. Key regression: GB content/serving byte-identical; the existing generic draft generator unchanged (brief/source None path); premium gate + per-market progress + E1 untouched.
- [ ] **Step 2: Frontend** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. All green; `no-literal-string` clean.
- [ ] **Step 3: iOS sync** — `cd frontend && npm run build && npx cap sync ios` (admin UI is web-only, but keep the bundle synced).
- [ ] **Step 4: Push + green CI** — `git push origin testing`; all jobs green.
- [ ] **Step 5: Promote (snapshot question)** — carries a prod migration (`market_briefs`). **Ask whether to snapshot prod first.** Merge testing→staging→main on green CI; then the manual Vercel prod deploy. Verify `/health` 200. **Pipeline ships inert** — no market is published; confirm a child sees no change (all markets except GB still `has_content=false`).
- [ ] **Step 6: Operator handoff (US pilot)** — document that an operator runs, in prod admin: generate+verify the US brief → scaffold US from GB → generate-market per level → **review/correct** each draft → approve → publish US. Note that go-live requires human review of regulatory accuracy (not automated).

---

## Self-Review

**Spec coverage:**
- Unit 1 `MarketBrief` model + migration → Task 1. ✓
- Unit 2 brief generate/verify + gate → Task 2. ✓
- Unit 3 market-aware generation (brief + GB ref) → Task 3. ✓
- Unit 4 scaffold from GB → Task 4. ✓
- Unit 5 publish/unpublish (guarded) → Task 5. ✓
- Unit 6 admin UI → Task 6. ✓
- Unit 7 US pilot → Task 7 Step 6 (operator handoff; the pipeline is proven by Tasks 2-4 tests with mocked LLM). ✓
- Non-goals respected: reuse existing generator/approve flow; no auto-publish; no all-9-markets in-build; GB unchanged. ✓
- Rollout: snapshot question + inert + testing→staging→main + Vercel → Task 7. ✓

**Placeholder scan:** The brief service + scaffold adapter show the prompt shape + key flow with the precise reuse points (`_generate_one`, `_system_prompt`, `approve_lesson_draft`, `require_verified_brief`); the implementer threads `brief`/`source_text` through the existing premium-client path. The endpoint/UI wiring are read-then-mirror against named existing endpoints. No TBDs in the model/migration/guard/publish code.

**Type/name consistency:** `MarketBrief` (Task 1) used by `require_verified_brief`/`generate_brief` (Task 2), `generate_market_level_lessons` (Task 3), `scaffold_market_from_gb` (Task 4). `require_verified_brief` defined in Task 2, used in Tasks 3+4. `has_content` flip (Task 5) gated on lessons created via the existing `approve_lesson_draft`. Migration `e4a7b2c1d0f3` chains `d3f6a9c0b1e2`. Endpoints: `/admin/markets/{code}/brief[/generate|/verify]`, `/scaffold`, `/publish`, `/unpublish`, `/admin/levels/{id}/generate-market` — consistent across backend (Tasks 2-5) and frontend (Task 6).
