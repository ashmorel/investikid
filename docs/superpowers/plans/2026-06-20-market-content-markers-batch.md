# Market Content — Markers, Replace & Batch Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show which levels already have published lessons, let a regenerate atomically REPLACE a level's lessons (committed only after review), and generate a whole module/market in rate-limit-aware batches.

**Architecture:** Two new admin backend endpoints (atomic `approve-drafts {replace}`; per-module `generate-market`) reuse the existing generation/approval pieces; the frontend adds a per-level published badge, replace controls on Market Content + the draft-review screen, and per-module / market-wide batch runners.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + pytest (backend); React 18 + Vite + TS + TanStack Query + vitest (frontend).

## Global Constraints
- Branch `testing`. **No DB migration.** Admin-gated; LLM endpoints `@limiter.limit("5/minute")` + `request: Request` param.
- Never read/modify any `.env`. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Drafts always require human review — these endpoints never auto-publish to children. Frontend strings via `t()` (admin namespace); `no-literal-string` is error-level.
- Promote `testing → staging → main`; manual Vercel prod for the admin bundle.

---

## Verified seams
- `app/models/content.py`: `Lesson(id, module_id, level_id, type, content_json, xp_reward, order_index)`; `Module(topic, order_index, market_code, …)`; `Level(module_id, order_index, …)`.
- `app/models/lesson_draft.py`: `LessonDraft(level_id, type, content_json, concept, moderation_safe, …)`.
- `app/routers/admin.py`: `approve_lesson_draft` (single: create `Lesson` order=max+1, delete draft, blocks `moderation_safe=false`); `generate_market_level_lessons_endpoint` (`POST /levels/{id}/generate-market`, body `GenerateMarketLessonsRequest{source_level_id}`, `require_verified_brief`); router is admin-gated; `func`, `select`, `Lesson`, `Module`, `Level`, `LessonDraft`, `require_verified_brief` already imported.
- `app/services/admin_content_generation_service.py`: `generate_market_level_lessons(session, target_level, *, source_level, brief) -> GenerationResult{created:list, skipped:int}` (already skips non-generatable `video` types); `_SCHEMA_HINT`.
- `app/services/market_brief_service.py`: `require_verified_brief(session, market_code) -> MarketBrief` (409 if unverified; `.brief_json`).
- Frontend `src/api/admin.ts`: `AdminLevel.lesson_count: number` (already present); `useLevels(moduleId)`, `useLevelLessons(levelId)`, `useApproveDraft(levelId)`, `useGenerateMarketLessons(levelId)`; query keys `['admin','level-drafts',levelId]`, `['admin','level-lessons',levelId]`, `['admin','modules']`, `['markets']`.
- Frontend `src/components/admin/MarketContent.tsx`: `LevelGenerator` (per-level row, `useGenerateMarketLessons`, deep-links to `/admin/modules/{moduleId}/levels/{levelId}/lessons`), `ModuleLessons`, `matchGbModule`. `src/components/admin/LessonDraftReview.tsx`: drafts list + per-draft approve via `useApproveDraft`. Admin i18n in `src/locales/en/admin.json` (`marketContent.*`, `draftReview.*`).

---

### Task 1: Backend — atomic approve-drafts (replace)

**Files:** Create `backend/app/services/lesson_approval_service.py`; Modify `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`; Test `backend/tests/test_approve_drafts.py`.

**Interfaces:**
- Produces: `approve_level_drafts(session, level, *, replace: bool) -> dict` returning `{"approved": int, "replaced": int, "skipped_unsafe": int}`; endpoint `POST /admin/levels/{level_id}/approve-drafts` body `ApproveDraftsRequest{replace: bool=False}` → `ApproveDraftsResult`.

- [ ] **Step 1: Failing test** — `backend/tests/test_approve_drafts.py`. Seed a Level with: 2 existing `Lesson`s, 2 `LessonDraft`s (`moderation_safe=True`) + 1 unsafe draft. Use `db_session`. Cover:
  - `replace=True` → existing 2 lessons deleted, 2 new lessons created from safe drafts, unsafe draft left, drafts for safe ones deleted; result `{approved:2, replaced:2, skipped_unsafe:1}`; final `Lesson` count under the level == 2.
  - `replace=False` → appends: final lesson count == 4 (2 old + 2 new), `replaced:0`.
  - **Empty-safe guard:** a level with existing lessons but ZERO safe drafts + `replace=True` → existing lessons NOT deleted (`approved:0, replaced:0`), lesson count unchanged.
  - Endpoint smoke via `admin_client`: `POST /admin/levels/{id}/approve-drafts {"replace":true}` → 200 with the result shape; 404 for an unknown level.

```python
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.services.lesson_approval_service import approve_level_drafts

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed(db_session, *, n_lessons, safe_drafts, unsafe_drafts):
    module = Module(topic="savings", title="Appr Mod", country_codes=[], is_premium=False,
                    order_index=950, icon="💵", market_code="US")
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="Appr L1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    for i in range(n_lessons):
        db_session.add(Lesson(module_id=module.id, level_id=level.id, type="card",
                              content_json={"title": f"old{i}", "body": "x"}, xp_reward=10, order_index=i))
    for i in range(safe_drafts):
        db_session.add(LessonDraft(level_id=level.id, type="card",
                                   content_json={"title": f"new{i}", "body": "y"}, concept="c",
                                   moderation_safe=True, moderation_category=None))
    for i in range(unsafe_drafts):
        db_session.add(LessonDraft(level_id=level.id, type="card",
                                   content_json={"title": f"bad{i}", "body": "z"}, concept="c",
                                   moderation_safe=False, moderation_category="x"))
    await db_session.flush()
    return level


async def _lesson_count(db_session, level_id):
    return await db_session.scalar(select(func.count(Lesson.id)).where(Lesson.level_id == level_id))


async def test_replace_deletes_old_and_creates_new(db_session):
    level = await _seed(db_session, n_lessons=2, safe_drafts=2, unsafe_drafts=1)
    res = await approve_level_drafts(db_session, level, replace=True)
    assert res == {"approved": 2, "replaced": 2, "skipped_unsafe": 1}
    assert await _lesson_count(db_session, level.id) == 2


async def test_no_replace_appends(db_session):
    level = await _seed(db_session, n_lessons=2, safe_drafts=2, unsafe_drafts=0)
    res = await approve_level_drafts(db_session, level, replace=False)
    assert res["approved"] == 2 and res["replaced"] == 0
    assert await _lesson_count(db_session, level.id) == 4


async def test_replace_with_no_safe_drafts_keeps_existing(db_session):
    level = await _seed(db_session, n_lessons=2, safe_drafts=0, unsafe_drafts=1)
    res = await approve_level_drafts(db_session, level, replace=True)
    assert res == {"approved": 0, "replaced": 0, "skipped_unsafe": 1}
    assert await _lesson_count(db_session, level.id) == 2  # NOT emptied
```

Run from `backend/`: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_approve_drafts.py -v` → FAIL (module missing).

- [ ] **Step 2: Implement the service** — `backend/app/services/lesson_approval_service.py`:

```python
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level
from app.models.lesson_draft import LessonDraft


async def approve_level_drafts(session: AsyncSession, level: Level, *, replace: bool) -> dict:
    """Approve all moderation-safe drafts for `level` into Lessons in one
    transaction. When `replace`, the level's existing Lessons are deleted FIRST —
    but only if there is at least one safe draft to replace them with, so an empty
    draft set never empties a published level. Unsafe drafts are left untouched."""
    drafts = (await session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == level.id)
    )).all()
    safe = [d for d in drafts if d.moderation_safe]
    skipped_unsafe = len(drafts) - len(safe)
    if not safe:
        return {"approved": 0, "replaced": 0, "skipped_unsafe": skipped_unsafe}

    replaced = 0
    if replace:
        existing = (await session.scalars(
            select(Lesson).where(Lesson.level_id == level.id)
        )).all()
        for lesson in existing:
            await session.delete(lesson)
        replaced = len(existing)
        await session.flush()

    base = (await session.scalar(
        select(func.max(Lesson.order_index)).where(Lesson.level_id == level.id)
    )) or 0
    for i, d in enumerate(safe, start=1):
        session.add(Lesson(
            module_id=level.module_id, level_id=level.id, type=d.type,
            content_json=d.content_json, xp_reward=10, order_index=base + i,
        ))
        await session.delete(d)
    await session.commit()
    return {"approved": len(safe), "replaced": replaced, "skipped_unsafe": skipped_unsafe}
```

- [ ] **Step 3: Schemas + endpoint** — in `backend/app/schemas/admin.py`:
```python
class ApproveDraftsRequest(BaseModel):
    replace: bool = False


class ApproveDraftsResult(BaseModel):
    approved: int
    replaced: int
    skipped_unsafe: int
```
In `backend/app/routers/admin.py` (add `approve_level_drafts` + the two schemas to the import blocks):
```python
@router.post("/levels/{level_id}/approve-drafts", response_model=ApproveDraftsResult)
async def approve_level_drafts_endpoint(
    level_id: uuid.UUID,
    payload: ApproveDraftsRequest,
    session: AsyncSession = Depends(get_session),
):
    level = await session.get(Level, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    return ApproveDraftsResult(**await approve_level_drafts(session, level, replace=payload.replace))
```

- [ ] **Step 4: Run + ruff + commit** — `pytest tests/test_approve_drafts.py -v` PASS; `ruff check .` clean.
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/lesson_approval_service.py backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_approve_drafts.py && git commit -m "feat(market): atomic approve-drafts with optional replace

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Backend — per-module batch generate

**Files:** Modify `backend/app/services/admin_content_generation_service.py`, `backend/app/routers/admin.py`, `backend/app/schemas/admin.py`; Test `backend/tests/test_module_batch_generate.py`.

**Interfaces:**
- Consumes: `generate_market_level_lessons(session, target_level, *, source_level, brief)` (Task-independent, existing).
- Produces: `generate_module_market_lessons(session, target_module, *, brief, include_populated) -> dict` → `{"levels": [{"level_id": str, "status": str, "created": int, "skipped": int}], "generated": int, "skipped_populated": int, "skipped_no_source": int, "errored": int}`; endpoint `POST /admin/modules/{module_id}/generate-market` body `GenerateModuleMarketRequest{include_populated: bool=False}`.

- [ ] **Step 1: Failing test** — `backend/tests/test_module_batch_generate.py`. Seed a GB module (topic="savings", order_index=10) with 2 levels (order 0,1) each holding a `card` Lesson; a US module (same topic+order_index) with 2 levels (order 0,1); the US level[0] ALREADY has a Lesson (populated), level[1] empty; a verified US `MarketBrief`. Patch `get_llm_client`/`moderate_output` (copy from `tests/test_market_content_generation.py`). Assert:
  - default (`include_populated=False`): level[0] → `skipped_populated`, level[1] → `generated` (drafts created); summary `generated:1, skipped_populated:1`.
  - `include_populated=True`: both levels generate.
  - A US module with NO matching GB module → all levels `skipped_no_source` (no crash).
  - Endpoint via `admin_client` returns the summary; 409 when the brief is unverified.

(Build the seed + mock in the established style; assert on the returned summary + `LessonDraft` counts.)

Run: `pytest tests/test_module_batch_generate.py -v` → FAIL.

- [ ] **Step 2: Implement the service** — add to `backend/app/services/admin_content_generation_service.py`:
```python
async def _gb_source_module(session, target_module: Module) -> Module | None:
    """Resolve the GB source module for a market module by the fields the scaffold
    preserves (topic + order_index). Returns None if not exactly one match."""
    rows = (await session.scalars(
        select(Module).where(
            Module.market_code == "GB",
            Module.topic == target_module.topic,
            Module.order_index == target_module.order_index,
        )
    )).all()
    return rows[0] if len(rows) == 1 else None


async def generate_module_market_lessons(
    session, target_module, *, brief, include_populated: bool
) -> dict:
    """Generate market drafts for every level in `target_module`, resolving each
    level's GB source by order_index. Skips levels that already have lessons
    unless `include_populated`. Best-effort per level."""
    gb_module = await _gb_source_module(session, target_module)
    target_levels = (await session.scalars(
        select(Level).where(Level.module_id == target_module.id).order_by(Level.order_index)
    )).all()
    gb_levels = (await session.scalars(
        select(Level).where(Level.module_id == gb_module.id).order_by(Level.order_index)
    )).all() if gb_module is not None else []
    gb_by_order: dict[int, list[Level]] = {}
    for lv in gb_levels:
        gb_by_order.setdefault(lv.order_index, []).append(lv)

    summary = {"levels": [], "generated": 0, "skipped_populated": 0,
               "skipped_no_source": 0, "errored": 0}
    for lvl in target_levels:
        entry = {"level_id": str(lvl.id), "status": "", "created": 0, "skipped": 0}
        src_matches = gb_by_order.get(lvl.order_index, [])
        if len(src_matches) != 1:
            entry["status"] = "skipped_no_source"
            summary["skipped_no_source"] += 1
            summary["levels"].append(entry)
            continue
        if not include_populated:
            count = await session.scalar(
                select(func.count(Lesson.id)).where(Lesson.level_id == lvl.id)
            )
            if count:
                entry["status"] = "skipped_populated"
                summary["skipped_populated"] += 1
                summary["levels"].append(entry)
                continue
        try:
            result = await generate_market_level_lessons(
                session, lvl, source_level=src_matches[0], brief=brief,
            )
            entry.update(status="generated", created=len(result.created), skipped=result.skipped)
            summary["generated"] += 1
        except Exception as exc:  # noqa: BLE001 — one level must not abort the module
            logger.warning("module batch gen failed for level %s: %s", lvl.id, exc)
            entry["status"] = "error"
            summary["errored"] += 1
        summary["levels"].append(entry)
    return summary
```
Ensure `logger` exists in the module (add `import logging; logger = logging.getLogger(__name__)` if absent) and `func` is imported from sqlalchemy.

- [ ] **Step 3: Schema + endpoint** — `GenerateModuleMarketRequest{include_populated: bool = False}` in `schemas/admin.py`. In `admin.py`:
```python
@router.post("/modules/{module_id}/generate-market")
@limiter.limit("5/minute")
async def generate_module_market_lessons_endpoint(
    request: Request,
    module_id: uuid.UUID,
    payload: GenerateModuleMarketRequest,
    session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    brief = await require_verified_brief(session, module.market_code)
    summary = await generate_module_market_lessons(
        session, module, brief=brief, include_populated=payload.include_populated,
    )
    return summary
```
(Add `generate_module_market_lessons` + `GenerateModuleMarketRequest` to the imports.)

- [ ] **Step 4: Run + ruff + commit**
```bash
cd /Users/leeashmore/investikid && git add backend/app/services/admin_content_generation_service.py backend/app/routers/admin.py backend/app/schemas/admin.py backend/tests/test_module_batch_generate.py && git commit -m "feat(market): per-module batch market-lesson generation (skip populated)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Frontend — published-lesson marker

**Files:** Modify `frontend/src/components/admin/MarketContent.tsx`, `frontend/src/locales/en/admin.json`; Test `frontend/src/components/admin/__tests__/MarketContent.test.tsx`.

**Interfaces:**
- Consumes: `AdminLevel.lesson_count` (existing). Produces: a badge in `LevelGenerator` reflecting `lesson_count`.

- [ ] **Step 1: Failing test** — extend `MarketContent.test.tsx`: a scaffolded US level whose `levelsByModule` entry has `lesson_count: 3` shows "3 published"; a level with `lesson_count: 0` shows the "no lessons yet" text. (The test mock's `Lvl` type may need a `lesson_count` field — add it to the mock data.) Run → FAIL.

- [ ] **Step 2: Implement** — in `LevelGenerator` (and the `ModuleLessons` mapping that builds each level row), read `lvl.lesson_count` and render a badge:
```tsx
{lessonCount > 0 ? (
  <span className="rounded bg-success-100 px-2 py-0.5 text-xs text-success-800">
    {t('marketContent.lessons.published', { count: lessonCount })}
  </span>
) : (
  <span className="text-xs text-muted-foreground">{t('marketContent.lessons.noneYet')}</span>
)}
```
Pass `lessonCount={lvl.lesson_count}` from `ModuleLessons` into `LevelGenerator` (extend its props). Add i18n keys `marketContent.lessons.published` ("{{count}} published") and `marketContent.lessons.noneYet` ("No lessons yet").

- [ ] **Step 3: Run + commit** — `cd frontend && npx vitest run src/components/admin/__tests__/MarketContent.test.tsx && npx tsc -b && npm run lint` green.
```bash
cd /Users/leeashmore/investikid && git add frontend/src/components/admin/MarketContent.tsx frontend/src/locales/en/admin.json frontend/src/components/admin/__tests__/MarketContent.test.tsx && git commit -m "feat(market): published-lesson badge per level

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Frontend — replace controls

**Files:** Modify `frontend/src/api/admin.ts`, `frontend/src/components/admin/LessonDraftReview.tsx`, `frontend/src/components/admin/MarketContent.tsx`, `frontend/src/locales/en/admin.json`; Test `frontend/src/components/admin/__tests__/LessonDraftReview.test.tsx`.

**Interfaces:**
- Consumes: `POST /admin/levels/{id}/approve-drafts {replace}` (Task 1). Produces: `useApproveDrafts(levelId)` hook; "Approve all" + "Publish & replace existing (N)" buttons.

- [ ] **Step 1: API hook** — in `src/api/admin.ts`:
```ts
export type ApproveDraftsResult = { approved: number; replaced: number; skipped_unsafe: number };
export function useApproveDrafts(levelId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (replace: boolean) =>
      adminFetch<ApproveDraftsResult>(`/admin/levels/${levelId}/approve-drafts`,
        { method: 'POST', body: JSON.stringify({ replace }) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'level-drafts', levelId] });
      qc.invalidateQueries({ queryKey: ['admin', 'level-lessons', levelId] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
    },
  });
}
```

- [ ] **Step 2: Failing test** — extend `LessonDraftReview.test.tsx` (it needs `levelId` + the existing-lesson count; the component will fetch lessons via `useLevelLessons`, so mock it): with drafts present and the level having ≥1 published lesson, a **"Publish & replace existing"** button appears; clicking it (through a confirm) calls the approve-drafts mutation with `replace=true`. An **"Approve all"** button calls it with `replace=false`. Run → FAIL.

- [ ] **Step 3: Implement** — in `LessonDraftReview.tsx`: call `useApproveDrafts(levelId)` and `useLevelLessons(levelId)` (for the existing count). When `drafts.length > 0`, render an "Approve all" button (`approveDrafts.mutate(false)`); when also `publishedCount > 0`, render "Publish & replace existing ({{count}})" guarded by the existing `ConfirmDialog` (message: replacing N lessons) → `approveDrafts.mutate(true)`. Keep per-draft approve/edit/regenerate/reject. Add i18n keys under `draftReview.*` (`approveAll`, `publishReplace`, `replaceConfirmTitle`, `replaceConfirmMessage`).

- [ ] **Step 4: Market Content "Regenerate (replace)" label** — in `MarketContent.tsx` `LevelGenerator`, when `lessonCount > 0` the generate button label becomes `t('marketContent.lessons.regenerateReplace')` ("Regenerate (replace)") and clicking first shows a `window.confirm`/`ConfirmDialog` with `t('marketContent.lessons.regenerateReplaceConfirm', {count})` before running the existing generate-market mutation (generation itself is unchanged; the replace happens at publish time on the review screen). Add those two keys.

- [ ] **Step 5: Run + commit** — `npx vitest run src/components/admin && npx tsc -b && npm run lint` green.
```bash
cd /Users/leeashmore/investikid && git add frontend/src/api/admin.ts frontend/src/components/admin frontend/src/locales/en/admin.json && git commit -m "feat(market): replace-on-publish controls (approve-all + publish-and-replace)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Frontend — batch generation runners

**Files:** Modify `frontend/src/api/admin.ts`, `frontend/src/components/admin/MarketContent.tsx`, `frontend/src/locales/en/admin.json`; Test `frontend/src/components/admin/__tests__/MarketContent.test.tsx`.

**Interfaces:**
- Consumes: `POST /admin/modules/{id}/generate-market {include_populated}` (Task 2). Produces: `useGenerateModuleLessons(moduleId)` hook; per-module + market-wide batch buttons.

- [ ] **Step 1: API hook** — in `src/api/admin.ts`:
```ts
export type ModuleBatchResult = {
  levels: { level_id: string; status: string; created: number; skipped: number }[];
  generated: number; skipped_populated: number; skipped_no_source: number; errored: number;
};
export function useGenerateModuleLessons(moduleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (include_populated: boolean) =>
      adminFetch<ModuleBatchResult>(`/admin/modules/${moduleId}/generate-market`,
        { method: 'POST', body: JSON.stringify({ include_populated }) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
    },
  });
}
```

- [ ] **Step 2: Failing test** — extend `MarketContent.test.tsx`: mock `useGenerateModuleLessons` so a per-module **"Generate all levels"** button calls the mutation with `include_populated=false`; and a market-wide **"Generate all"** runs each module's batch in sequence (assert the per-module mutate is called once per module). Mock the hooks per the file's existing `vi.mock('@/api/admin', …)` pattern. Run → FAIL.

- [ ] **Step 3: Implement** — in `MarketContent.tsx`:
  - `ModuleLessons` gets a **"Generate all levels"** button → `useGenerateModuleLessons(mod.id).mutate(includePopulated)`, showing the returned summary (`generated`/`skipped_populated`/`errored`).
  - A market-level **"Generate all"** control: a small runner that iterates `marketModules` and, for each, awaits the per-module batch sequentially, tracking progress (`module i of N`) in local state, continuing past a rejected module (catch + record), and surfacing a per-module result list. Because each module = one rate-limited endpoint call, space calls by awaiting each before the next; on a `429` (`ApiError.status === 429`) wait and retry that module once. An **"include levels that already have lessons"** checkbox feeds `include_populated`.
  - Keep the existing per-level generate control (Task 4) intact.
  Add i18n keys under `marketContent.batch.*` (`generateAllLevels`, `generateAllMarket`, `includePopulated`, `progress` = "Module {{i}} of {{n}}", `moduleResult` = "{{generated}} generated, {{skipped}} skipped", `moduleFailed`).

- [ ] **Step 4: Run + commit** — `npx vitest run src/components/admin && npx tsc -b && npm run lint && npm run build` green.
```bash
cd /Users/leeashmore/investikid && git add frontend/src/api/admin.ts frontend/src/components/admin frontend/src/locales/en/admin.json && git commit -m "feat(market): per-module + market-wide batch generation runners

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Full verification + promote

- [ ] **Step 1: Backend** — `cd backend && ruff check . && pytest tests/test_approve_drafts.py tests/test_module_batch_generate.py tests/test_market_content_generation.py tests/test_lesson_draft_endpoints.py -q`. Green.
- [ ] **Step 2: Frontend** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. Green; `no-literal-string` clean.
- [ ] **Step 3: iOS sync** — `cd frontend && npm run build && npx cap sync ios` (admin UI is web; keep the bundle synced).
- [ ] **Step 4: Push + green CI** — `git push origin testing`; all 5 jobs green.
- [ ] **Step 5: Promote** — **No migration → no snapshot question.** Merge `testing → staging → main` on green CI; manual `vercel deploy --prod --archive=tgz --yes` + alias `app.investikid.ai`; verify `/health` 200 and `POST /admin/levels/<uuid>/approve-drafts` + `POST /admin/modules/<uuid>/generate-market` return **401/403** unauth (gated, deployed) not 404.
- [ ] **Step 6: Update trackers** (standing rule) — note the operator tooling in `docs/MASTER-BACKLOG.md` (Live in prod) / the roadmap.

---

## Self-Review

**Spec coverage:**
- Unit A marker → Task 3. ✓
- Unit B atomic approve-drafts replace (delete-on-commit, empty-safe guard) + Market Content "Regenerate (replace)" + review-screen "Publish & replace" → Tasks 1 (backend) + 4 (frontend). ✓
- Unit C per-module batch (GB-source resolution, skip-populated default + toggle, best-effort) + per-module button + market-wide sequential rate-limit-aware runner → Tasks 2 (backend) + 5 (frontend). ✓
- Non-goals respected: no auto-publish (drafts still reviewed), no async jobs (client-sequential), no migration, suggester untouched. ✓
- Rollout/testing → Task 6. ✓

**Placeholder scan:** full code for the approval service, the batch service + GB resolution, the schemas/endpoints, the marker badge, and the API hooks. The frontend test/UI steps are read-then-mirror against named seams (`AdminLevel.lesson_count`, `useLevelLessons`, `ConfirmDialog`, the existing `vi.mock('@/api/admin')` pattern) with concrete key names — no TBDs.

**Type/name consistency:** `approve_level_drafts(...) -> {approved,replaced,skipped_unsafe}` (Task 1) ↔ `ApproveDraftsResult` ↔ `useApproveDrafts` (Task 4). `generate_module_market_lessons(...)` summary shape (Task 2) ↔ `ModuleBatchResult` ↔ `useGenerateModuleLessons` (Task 5). `AdminLevel.lesson_count` drives the marker (Task 3) and the "Regenerate (replace)" gating (Task 4). Endpoints `/levels/{id}/approve-drafts` and `/modules/{id}/generate-market` are named identically across backend + frontend. No migration anywhere.
