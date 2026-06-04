# Next-Quest Resolver + Consistent Back Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the false "You've finished everything" Home state with a server-side next-lesson resolver that always points to the true next quest, and add a consistent, accessible Back button across all child drill-down pages.

**Architecture:** A new backend service computes the next actionable lesson across all accessible modules (reusing `level_service.derive_level_states` — the same locking/completion truth the level screens use) and a `GET /next-lesson` endpoint exposes it. The Home `useNextLesson` hook collapses to one call to that endpoint; `caught_up` becomes "resolver returned null". A reusable `BackButton` replaces the inconsistent text back-links on the drill-down pages and fills the Market gap.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async (backend); React 18 + Vite + TS + TanStack Query + Tailwind v4 + Vitest/vitest-axe (frontend).

---

## Reference facts (verified — read before starting)

- **Spec:** `invest-ed/docs/superpowers/specs/2026-06-04-next-quest-and-back-nav-design.md`.
- **Root cause (Fix 1):** `useNextLesson` picks ONE target module (recs → else first unlocked module by `order_index`) and declares global `caught_up` from that one module's level state. `get_recommendations` returns empty lists when `user.profiling_enabled` is false (DB default false), so the fallback "first module" path dominates → once module 1 is complete, the hero falsely says "finished everything".
- **Locking/completion truth** lives in `app/services/level_service.py::derive_level_states(levels, *, lessons_by_level, completed_ids, scores, user_is_premium)` returning `{level_id: LevelState(state, locked_reason, passed, lessons_total, lessons_completed)}` where `state ∈ {"in_progress","completed","locked"}`. `list_levels` (`app/routers/content.py:137-184`) is the canonical usage — mirror it exactly.
- **Content router has NO prefix** (`router = APIRouter(tags=["content"])`, included at `app/main.py:161`). Sibling endpoints live at root: `/modules`, `/modules/{id}/levels`, `/levels/{id}/lessons`. So the new endpoint is `GET /next-lesson`, and the FE client calls `apiFetch('/next-lesson')`.
- **Helpers to reuse:** `app/services/content_service.py::content_region_for`, `::is_module_accessible`, `::derive_lesson_title`; `app/services/entitlements.py::is_premium`. Models: `app/models/content.py` `Module`, `Level`, `Lesson`, `LessonCompletion`.
- **Model fields:** `Level(id, module_id, title, order_index, is_premium, pass_threshold, content_source, icon)`; `Lesson(id, module_id, level_id|None, type, content_json, xp_reward, order_index)`; `LessonCompletion(id, user_id, lesson_id, completed_at, score|None)`; `Module(... country_codes, is_premium, order_index, icon, title, topic)`.
- **Test pattern (mirror `tests/test_levels.py`):** `pytestmark = pytest.mark.asyncio(loop_scope="session")`; `_login(client, email, username)` registers (`country_code="GB"`) + logs in + sets CSRF header; build content with `db_session` (`Module(...)`, `Level(...)`, `Lesson(...)`, `await db_session.flush()`). Register a completion with `LessonCompletion(user_id=<user id>, lesson_id=<id>, score=<float|None>)`. The local test Postgres can hang ~90s+ after a killed run — environmental; rely on CI.
- **FE `useNextLesson` consumers:** only `HomeHero.tsx` (`src/components/child/HomeHero.tsx`). The `NextLesson` shape it relies on: `{ mode, moduleTitle, moduleIcon, lessonLabel, to, isLoading }`. `pickTargetModule/pickTargetLevel/pickTargetLesson` (in `src/lib/homeHero.ts`) are used ONLY by `useNextLesson` (verify with grep before deleting). `buildHeroGreeting` (same file) is also used by HomeHero — KEEP it.
- **FE sub-page back-links to replace:** `Module.tsx` (`← Back to modules` → `/lessons`), `Level.tsx` (`← Back to levels` → `/lessons/{moduleId}`), `Lesson.tsx` (`← Back to module` → currently `/lessons/{moduleId}`; new target `/lessons/{moduleId}/{levelId}`), `Stock.tsx` (`← Back to market` → `/simulator/market`), `Market.tsx` (NONE → add `/simulator`). Leave `Coach.tsx` as-is.

## Commands

- Backend (from `invest-ed/backend`): test `/Users/leeashmore/Local Repo/.venv/bin/pytest`; lint `/Users/leeashmore/Local Repo/.venv/bin/ruff check .`.
- Frontend (from `invest-ed/frontend`): `npx tsc -b`; `npm run lint` (known-OK warnings: `button.tsx` + `Market.tsx` react-refresh); `npm test`; `npm run build`.
- Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end every commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. NEVER read/modify any `.env`. CI's 6 jobs gate the Railway deploy.

---

## Task 1: Next-lesson resolver service + schema

**Files:**
- Modify: `invest-ed/backend/app/schemas/content.py` (add `NextLessonOut`)
- Create: `invest-ed/backend/app/services/next_lesson_service.py`
- Test: `invest-ed/backend/tests/test_next_lesson_service.py`

- [ ] **Step 1: Add the `NextLessonOut` schema**

In `invest-ed/backend/app/schemas/content.py`, add (match the file's existing pydantic style; `uuid`/`BaseModel` are imported there — add `from typing import Literal` if not present):

```python
class NextLessonOut(BaseModel):
    module_id: uuid.UUID
    module_title: str
    module_icon: str | None
    level_id: uuid.UUID
    lesson_id: uuid.UUID
    lesson_title: str
    mode: Literal["start", "continue"]
```

- [ ] **Step 2: Write the failing service test**

Create `invest-ed/backend/tests/test_next_lesson_service.py` (mirror `tests/test_levels.py` for content/user setup; resolve the registered user via the DB). Use the `client` fixture to register/login a user, then fetch that `User` from `db_session` to pass to the service.

```python
import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.user import User
from app.services.next_lesson_service import resolve_next_lesson

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {"password": "SecurePass123!", "dob": "2006-01-01", "country_code": "GB", "currency_code": "GBP"}


async def _register(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _get_user(db_session, email) -> User:
    return await db_session.scalar(select(User).where(User.email == email))


async def _module(db_session, title, order_index, *, lessons_per_level=1, levels=1):
    m = Module(topic="stocks", title=title, country_codes=[], is_premium=False, order_index=order_index, icon="📈")
    db_session.add(m)
    await db_session.flush()
    made = []
    for li in range(levels):
        lv = Level(module_id=m.id, title=f"{title} L{li}", order_index=li, is_premium=False, pass_threshold=0.7)
        db_session.add(lv)
        await db_session.flush()
        lessons = []
        for pi in range(lessons_per_level):
            lsn = Lesson(module_id=m.id, level_id=lv.id, type="card", order_index=pi, xp_reward=10,
                         content_json={"title": f"{title}-{li}-{pi}", "body": "b"})
            db_session.add(lsn)
            lessons.append(lsn)
        await db_session.flush()
        made.append((lv, lessons))
    return m, made


async def _complete(db_session, user, lesson):
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, score=1.0))
    await db_session.flush()


async def test_new_user_gets_first_module_first_lesson(client, db_session):
    await _register(client, "nl1@example.com", "nl1user")
    user = await _get_user(db_session, "nl1@example.com")
    m, made = await _module(db_session, "Mod A", 0)
    result = await resolve_next_lesson(db_session, user)
    assert result is not None
    assert result.module_id == m.id
    assert result.lesson_id == made[0][1][0].id
    assert result.mode == "start"


async def test_first_module_done_returns_second_module(client, db_session):
    # THE REPORTED BUG: module 1 complete, module 2 incomplete → must return module 2's lesson
    await _register(client, "nl2@example.com", "nl2user")
    user = await _get_user(db_session, "nl2@example.com")
    m1, made1 = await _module(db_session, "Mod 1", 0)
    m2, made2 = await _module(db_session, "Mod 2", 1)
    await _complete(db_session, user, made1[0][1][0])  # finish module 1's only lesson
    result = await resolve_next_lesson(db_session, user)
    assert result is not None
    assert result.module_id == m2.id
    assert result.lesson_id == made2[0][1][0].id
    assert result.mode == "start"


async def test_all_complete_returns_none(client, db_session):
    await _register(client, "nl3@example.com", "nl3user")
    user = await _get_user(db_session, "nl3@example.com")
    m, made = await _module(db_session, "Only Mod", 0)
    await _complete(db_session, user, made[0][1][0])
    result = await resolve_next_lesson(db_session, user)
    assert result is None


async def test_partial_module_is_continue(client, db_session):
    await _register(client, "nl4@example.com", "nl4user")
    user = await _get_user(db_session, "nl4@example.com")
    m, made = await _module(db_session, "Two Lessons", 0, lessons_per_level=2)
    await _complete(db_session, user, made[0][1][0])  # 1 of 2 done
    result = await resolve_next_lesson(db_session, user)
    assert result is not None
    assert result.lesson_id == made[0][1][1].id
    assert result.mode == "continue"
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_next_lesson_service.py -v`
Expected: FAIL — `ModuleNotFoundError`/`ImportError: cannot import name 'resolve_next_lesson'`.

- [ ] **Step 4: Implement the resolver**

Create `invest-ed/backend/app/services/next_lesson_service.py`:

```python
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.schemas.content import NextLessonOut
from app.services.content_service import (
    content_region_for,
    derive_lesson_title,
    is_module_accessible,
)
from app.services.entitlements import is_premium
from app.services.level_service import LevelStateInput, derive_level_states


async def resolve_next_lesson(session: AsyncSession, user: Any) -> NextLessonOut | None:
    """Return the user's next actionable lesson across all accessible modules,
    or None when genuinely caught up. Reuses derive_level_states so locking and
    completion match the level screens exactly."""
    modules = list(await session.scalars(select(Module).order_by(Module.order_index)))
    for m in modules:
        if not is_module_accessible(
            content_region_for(user), is_premium(user), m.country_codes, m.is_premium
        ):
            continue

        levels = list(await session.scalars(
            select(Level).where(Level.module_id == m.id).order_by(Level.order_index)
        ))
        if not levels:
            continue

        lessons = list(await session.scalars(
            select(Lesson).where(Lesson.module_id == m.id)
        ))
        lessons_by_level: dict = {}
        for lsn in lessons:
            if lsn.level_id is not None:
                lessons_by_level.setdefault(lsn.level_id, []).append(lsn.id)

        all_lesson_ids = [lsn.id for lsn in lessons]
        completed_ids: set = set()
        scores: dict = {}
        if all_lesson_ids:
            rows = (await session.execute(
                select(LessonCompletion.lesson_id, LessonCompletion.score).where(
                    LessonCompletion.user_id == user.id,
                    LessonCompletion.lesson_id.in_(all_lesson_ids),
                )
            )).all()
            for lid, score in rows:
                completed_ids.add(lid)
                scores[lid] = score

        states = derive_level_states(
            [LevelStateInput(lv.id, lv.order_index, lv.is_premium, lv.pass_threshold) for lv in levels],
            lessons_by_level=lessons_by_level,
            completed_ids=completed_ids, scores=scores,
            user_is_premium=is_premium(user),
        )
        module_has_completion = any(lid in completed_ids for lid in all_lesson_ids)

        for lv in sorted(levels, key=lambda x: x.order_index):
            st = states[lv.id]
            if st.state == "locked" or st.lessons_completed >= st.lessons_total:
                continue
            level_lessons = sorted(
                [lsn for lsn in lessons if lsn.level_id == lv.id],
                key=lambda x: x.order_index,
            )
            target = next((lsn for lsn in level_lessons if lsn.id not in completed_ids), None)
            if target is None:
                continue
            return NextLessonOut(
                module_id=m.id, module_title=m.title, module_icon=m.icon,
                level_id=lv.id, lesson_id=target.id,
                lesson_title=derive_lesson_title(target.type, target.content_json or {}),
                mode="continue" if module_has_completion else "start",
            )
    return None
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_next_lesson_service.py -v`
Expected: 4 passed. (If the DB hangs ~90s+, it's environmental — rely on CI.)

- [ ] **Step 6: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/next_lesson_service.py app/schemas/content.py tests/test_next_lesson_service.py
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/content.py invest-ed/backend/app/services/next_lesson_service.py invest-ed/backend/tests/test_next_lesson_service.py
git commit -m "feat(next-lesson): resolver service for the true next actionable lesson

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `GET /next-lesson` endpoint

**Files:**
- Modify: `invest-ed/backend/app/routers/content.py` (new route + import)
- Test: `invest-ed/backend/tests/test_next_lesson_endpoint.py`

- [ ] **Step 1: Write the failing endpoint test**

Create `invest-ed/backend/tests/test_next_lesson_endpoint.py` (reuse the helpers from Task 1's test style):

```python
import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

_USER = {"password": "SecurePass123!", "dob": "2006-01-01", "country_code": "GB", "currency_code": "GBP"}


async def _register(client, email, username):
    await client.post("/auth/register", json={**_USER, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _one_module(db_session, title="Mod", order_index=0):
    m = Module(topic="stocks", title=title, country_codes=[], is_premium=False, order_index=order_index, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L0", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lsn = Lesson(module_id=m.id, level_id=lv.id, type="card", order_index=0, xp_reward=10,
                 content_json={"title": "Intro", "body": "b"})
    db_session.add(lsn)
    await db_session.flush()
    return m, lv, lsn


async def test_next_lesson_returns_envelope(client, db_session):
    await _register(client, "ep1@example.com", "ep1user")
    m, lv, lsn = await _one_module(db_session)
    r = await client.get("/next-lesson")
    assert r.status_code == 200
    body = r.json()
    assert body["next"] is not None
    assert body["next"]["module_id"] == str(m.id)
    assert body["next"]["lesson_id"] == str(lsn.id)
    assert body["next"]["mode"] == "start"


async def test_next_lesson_null_when_caught_up(client, db_session):
    await _register(client, "ep2@example.com", "ep2user")
    m, lv, lsn = await _one_module(db_session)
    user = await db_session.scalar(select(User).where(User.email == "ep2@example.com"))
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lsn.id, score=1.0))
    await db_session.flush()
    r = await client.get("/next-lesson")
    assert r.status_code == 200
    assert r.json()["next"] is None


async def test_next_lesson_requires_auth(client):
    r = await client.get("/next-lesson")
    assert r.status_code == 401
```

> Note: tests share a session-scoped DB; if an earlier test's modules persist, assert on the specific module/lesson IDs you created (as above) rather than absolute counts. If global content from other tests interferes, scope your created module's `order_index` low and assert `body["next"]` is not None + your created IDs are reachable; adjust to the suite's isolation (mirror how `test_levels.py` handles it).

- [ ] **Step 2: Run to verify failure**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_next_lesson_endpoint.py -v`
Expected: FAIL — 404 (route not defined) on the GET.

- [ ] **Step 3: Add the endpoint**

In `invest-ed/backend/app/routers/content.py`, add the import near the other service imports:

```python
from app.services.next_lesson_service import resolve_next_lesson
```
Add the schema to the existing `app.schemas.content` import line: include `NextLessonOut`.
Add a small envelope model + route (place near `list_modules`):

```python
from pydantic import BaseModel  # if not already imported at top


class NextLessonEnvelope(BaseModel):
    next: NextLessonOut | None


@router.get("/next-lesson", response_model=NextLessonEnvelope)
async def get_next_lesson(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return NextLessonEnvelope(next=await resolve_next_lesson(session, current_user))
```
(If `BaseModel` import or an envelope location is awkward, define `NextLessonEnvelope` in `app/schemas/content.py` next to `NextLessonOut` and import it — either is fine; keep it consistent with the file's conventions.)

- [ ] **Step 4: Run tests to verify pass**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_next_lesson_endpoint.py -v`
Expected: 3 passed.

- [ ] **Step 5: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/content.py invest-ed/backend/app/schemas/content.py invest-ed/backend/tests/test_next_lesson_endpoint.py
git commit -m "feat(next-lesson): GET /next-lesson endpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Frontend — wire `useNextLesson` to the resolver

**Files:**
- Modify: `invest-ed/frontend/src/api/content.ts` (type + client)
- Modify: `invest-ed/frontend/src/hooks/useNextLesson.ts`
- Modify: `invest-ed/frontend/src/lib/homeHero.ts` (remove dead pickTarget* helpers)
- Modify: `invest-ed/frontend/src/lib/__tests__/homeHero.test.ts` (drop pickTarget* cases, keep buildHeroGreeting)
- Test: `invest-ed/frontend/src/hooks/__tests__/useNextLesson.test.tsx` (new)

- [ ] **Step 1: Add the FE type + API client**

In `invest-ed/frontend/src/api/content.ts`, add a type and a client method:

```typescript
export type NextLesson = {
  module_id: string;
  module_title: string;
  module_icon: string | null;
  level_id: string;
  lesson_id: string;
  lesson_title: string;
  mode: 'start' | 'continue';
};
```
Add to `contentApi`:
```typescript
  nextLesson: () => apiFetch<{ next: NextLesson | null }>('/next-lesson'),
```

- [ ] **Step 2: Verify pickTarget* helpers are unused elsewhere**

Run: `cd invest-ed/frontend && grep -rn "pickTargetModule\|pickTargetLevel\|pickTargetLesson" src/ | grep -v "homeHero"`
Expected: no output (only `homeHero.ts` + its test reference them). If anything else uses them, STOP and report.

- [ ] **Step 3: Write the failing hook test**

Create `invest-ed/frontend/src/hooks/__tests__/useNextLesson.test.tsx` (match the repo's hook-test setup — QueryClientProvider wrapper; mock `@/api/content`). Example:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useNextLesson } from '../useNextLesson';
import { contentApi } from '@/api/content';

vi.mock('@/api/content', async (orig) => {
  const actual = await orig<typeof import('@/api/content')>();
  return { ...actual, contentApi: { ...actual.contentApi, nextLesson: vi.fn() } };
});

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useNextLesson', () => {
  it('maps a resolved lesson to start/continue with a deep-link', async () => {
    (contentApi.nextLesson as ReturnType<typeof vi.fn>).mockResolvedValue({
      next: { module_id: 'm1', module_title: 'Mod', module_icon: '📈', level_id: 'l1', lesson_id: 'q1', lesson_title: 'Intro', mode: 'start' },
    });
    const { result } = renderHook(() => useNextLesson(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.mode).toBe('start');
    expect(result.current.to).toBe('/lessons/m1/l1/q1');
    expect(result.current.lessonLabel).toBe('Intro');
  });

  it('reports caught_up when resolver returns null', async () => {
    (contentApi.nextLesson as ReturnType<typeof vi.fn>).mockResolvedValue({ next: null });
    const { result } = renderHook(() => useNextLesson(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.mode).toBe('caught_up');
    expect(result.current.to).toBeNull();
  });
});
```

- [ ] **Step 4: Run to verify failure**

Run: `cd invest-ed/frontend && npm test -- useNextLesson`
Expected: FAIL (hook still uses the old multi-query implementation / mock not consumed).

- [ ] **Step 5: Rewrite `useNextLesson`**

Replace the body of `invest-ed/frontend/src/hooks/useNextLesson.ts` with a single-query implementation (keep the exported `NextLesson` interface shape that `HomeHero` consumes — note this is the *hook's* return interface, distinct from the api `NextLesson` payload type; keep the existing interface name/exports):

```tsx
import { useQuery } from '@tanstack/react-query';
import { contentApi } from '@/api/content';
import type { HeroMode } from '@/lib/homeHero';

export interface NextLesson {
  mode: HeroMode;
  moduleId: string | null;
  levelId: string | null;
  lessonId: string | null;
  moduleTitle: string | null;
  moduleIcon: string | null;
  lessonLabel: string | null;
  to: string | null;
  isLoading: boolean;
}

export function useNextLesson(): NextLesson {
  const { data, isLoading } = useQuery({
    queryKey: ['next-lesson'],
    queryFn: () => contentApi.nextLesson(),
    retry: false,
    staleTime: 60_000,
  });

  if (isLoading) {
    return { mode: 'start', moduleId: null, levelId: null, lessonId: null, moduleTitle: null, moduleIcon: null, lessonLabel: null, to: null, isLoading: true };
  }

  const next = data?.next ?? null;
  if (!next) {
    return { mode: 'caught_up', moduleId: null, levelId: null, lessonId: null, moduleTitle: null, moduleIcon: null, lessonLabel: null, to: null, isLoading: false };
  }

  return {
    mode: next.mode,
    moduleId: next.module_id,
    levelId: next.level_id,
    lessonId: next.lesson_id,
    moduleTitle: next.module_title,
    moduleIcon: next.module_icon,
    lessonLabel: next.lesson_title,
    to: `/lessons/${next.module_id}/${next.level_id}/${next.lesson_id}`,
    isLoading: false,
  };
}
```

- [ ] **Step 6: Remove the dead pickTarget* helpers**

In `invest-ed/frontend/src/lib/homeHero.ts`, delete `pickTargetModule`, `pickTargetLevel`, `pickTargetLesson` and the now-unused imports (`ModuleOut`, `LevelOut`, `LessonSummary`, `CategorisedRecommendations`, `TargetModule`). KEEP `HeroMode`, `HeroGreetingCtx`, and `buildHeroGreeting`. In `src/lib/__tests__/homeHero.test.ts`, delete the `describe('pickTargetModule'...)` / `pickTargetLevel` / `pickTargetLesson` blocks and their imports; keep the `buildHeroGreeting` tests.

- [ ] **Step 7: Run hook + greeting tests + tsc**

Run: `cd invest-ed/frontend && npm test -- useNextLesson homeHero && npx tsc -b`
Expected: hook 2 tests pass; homeHero greeting tests pass; tsc clean. (HomeHero.tsx needs no change — it reads `next.mode`/`next.to`/`next.lessonLabel` which are preserved.)

- [ ] **Step 8: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/content.ts invest-ed/frontend/src/hooks/useNextLesson.ts invest-ed/frontend/src/hooks/__tests__/useNextLesson.test.tsx invest-ed/frontend/src/lib/homeHero.ts invest-ed/frontend/src/lib/__tests__/homeHero.test.ts
git commit -m "feat(next-lesson): wire Home hero to the next-lesson resolver; drop client-side picking

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `BackButton` component

**Files:**
- Create: `invest-ed/frontend/src/components/child/BackButton.tsx`
- Test: `invest-ed/frontend/src/components/child/__tests__/BackButton.test.tsx`

- [ ] **Step 1: Write the failing component test**

Create `invest-ed/frontend/src/components/child/__tests__/BackButton.test.tsx` (match sibling tests' setup; `BackButton` renders a router `<Link>`, so wrap in `MemoryRouter`):

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { BackButton } from '../BackButton';

function wrap(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('BackButton', () => {
  it('links to the target with an accessible name', () => {
    wrap(<BackButton to="/simulator" label="Simulator" />);
    const link = screen.getByRole('link', { name: /back to simulator/i });
    expect(link).toHaveAttribute('href', '/simulator');
    expect(link).toHaveTextContent('Simulator');
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<BackButton to="/lessons" label="Quests" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd invest-ed/frontend && npm test -- BackButton`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `BackButton`**

Create `invest-ed/frontend/src/components/child/BackButton.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

export function BackButton({ to, label, className }: { to: string; label: string; className?: string }) {
  return (
    <Link
      to={to}
      aria-label={`Back to ${label}`}
      className={cn(
        'inline-flex min-h-[44px] items-center gap-1 rounded-lg px-2 py-2 text-base font-semibold text-brand-700 transition-colors hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400',
        className,
      )}
    >
      <ChevronLeft className="h-5 w-5" aria-hidden="true" />
      <span>{label}</span>
    </Link>
  );
}
```
(`lucide-react` and `cn` are already used across the app — confirm `ChevronLeft` imports cleanly; if the app prefers a text arrow, use `<span aria-hidden>←</span>` instead.)

- [ ] **Step 4: Run to verify pass**

Run: `cd invest-ed/frontend && npm test -- BackButton && npx tsc -b`
Expected: 2 passed; tsc clean.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/BackButton.tsx invest-ed/frontend/src/components/child/__tests__/BackButton.test.tsx
git commit -m "feat(nav): reusable accessible BackButton for child sub-pages

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Mount `BackButton` on drill-down pages (replace text links, fill Market)

**Files:**
- Modify: `invest-ed/frontend/src/pages/child/Module.tsx`, `Level.tsx`, `Lesson.tsx`, `Market.tsx`, `Stock.tsx`

- [ ] **Step 1: Read each page, then replace/add the back affordance**

For each page, READ it first and import `BackButton`:
```tsx
import { BackButton } from '@/components/child/BackButton';
```
Then place `<BackButton .../>` in a consistent slot at the top of the page's content (above the heading), and DELETE the old underlined text back-links. Targets:
- `Module.tsx` — replace both `← Back to modules` links with `<BackButton to="/lessons" label="Quests" />`.
- `Level.tsx` — replace the `← Back to levels` links with `<BackButton to={`/lessons/${moduleId ?? ''}`} label="Levels" />`.
- `Lesson.tsx` — replace the `← Back to module` link with `<BackButton to={`/lessons/${moduleId ?? ''}/${levelId ?? ''}`} label="Lessons" />` (use the page's existing `moduleId`/`levelId` params; keep the in-player `onBack` `navigate(-1)` as-is).
- `Market.tsx` — ADD `<BackButton to="/simulator" label="Simulator" />` at the top of the header (it currently has none).
- `Stock.tsx` — replace the `← Back to market` links with `<BackButton to="/simulator/market" label="Market" />`.

Do not change any data fetching, params, or other layout. Keep error/empty branches working (if a back link sits inside an error branch, keep a BackButton there too).

- [ ] **Step 2: Typecheck + lint + run page tests**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test -- Module Level Lesson Market Stock`
Expected: tsc clean; lint clean (known warnings only); page tests pass. Update any test that asserted on the old `← Back to …` text to expect the BackButton's accessible name (`Back to {label}`) instead.

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Module.tsx invest-ed/frontend/src/pages/child/Level.tsx invest-ed/frontend/src/pages/child/Lesson.tsx invest-ed/frontend/src/pages/child/Market.tsx invest-ed/frontend/src/pages/child/Stock.tsx
git commit -m "feat(nav): consistent BackButton on all child drill-down pages (incl. Market)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Full regression + push

- [ ] **Step 1: Backend regression**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest`
Expected: ruff clean; tests pass (rely on CI if local DB hangs).

- [ ] **Step 2: Frontend regression**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean except the known `button.tsx` + `Market.tsx` warnings; all tests pass; build OK.

- [ ] **Step 3: Push + watch CI**

```bash
cd "/Users/leeashmore/Local Repo"
git push origin main
```
Confirm all 6 CI jobs green.

- [ ] **Step 4: Manual verification note (report to user)**

Note in the close-out: this is a web/child change (no `npx cap sync ios` needed). The reported bug's acceptance check: with module 1 complete and module 2 incomplete, the Home hero now shows a "Continue/Start" card pointing at module 2's next lesson instead of "You've finished everything".

---

## Self-review notes

- **Spec coverage:** Fix 1 resolver + endpoint (T1, T2), FE rewire + dead-code removal (T3), all backend test cases incl. the reported bug, locked-remainder (covered by `derive_level_states` skipping locked levels + the cross-module loop), all-complete→null, premium/region gating (via `is_module_accessible` + `derive_level_states`). Fix 2 BackButton (T4) + mounting incl. Market gap (T5). Regression/push (T6).
- **Placeholder scan:** concrete code + tests in every step; the one judgement note (test isolation on a shared session DB) tells the implementer to assert on created IDs.
- **Type consistency:** api payload type `NextLesson` (snake_case fields) vs the hook's return interface `NextLesson` (camelCase) are deliberately distinct — the hook maps payload→interface in T3 Step 5; `mode` values `start|continue|caught_up` consistent with `HeroMode`. `NextLessonOut` fields match between schema (T1), service return (T1 Step 4), and FE payload type (T3 Step 1).
- **Locked-remainder coverage:** consider adding (optional) a backend test where module 1's level 2 is `is_premium=True` for a free user with level 1 complete → resolver skips to module 2; the existing 4 cases already prove the cross-module fallthrough, so this is a nice-to-have.
