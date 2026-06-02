# Child Home Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat child home with a Coach-Eddie-led hero that surfaces the actual next lesson (Start/Continue), with an instant templated greeting for all users and a premium AI-personalised greeting that progressively swaps in.

**Architecture:** Pure helpers resolve the next lesson + build the templated greeting from already-fetched data. A `useNextLesson` hook fetches the chosen module's levels/lessons. `HomeHero` renders the templated line instantly and, for premium users, swaps in a moderated AI line from a new premium-gated `POST /ai/home-greeting` (reusing the Coach Eddie LLM + moderation stack). Templated line is the guaranteed fallback.

**Tech Stack:** React 18 + TS + TanStack Query + Tailwind + framer-motion; FastAPI + SQLAlchemy async; Pydantic v2; Vitest + vitest-axe; Pytest (async, `loop_scope="session"`).

**Spec:** `docs/superpowers/specs/2026-06-02-child-home-redesign-design.md`

**Conventions:**
- Backend from `invest-ed/backend`: tests `/Users/leeashmore/Local\ Repo/.venv/bin/pytest`, lint `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`. Tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session` fixtures; mock the LLM + `moderate_output` the same way the existing Coach Eddie endpoint tests do (find them with `grep -rl "tutor/coach\|coach" tests/`).
- Frontend from `invest-ed/frontend`: `npx tsc -b`, `npm run lint` (only the pre-existing `button.tsx` fast-refresh warning is acceptable), `npm test`, `npm run build`.
- Git from `/Users/leeashmore/Local Repo`; commit to `main`; trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend only on green CI (5 jobs).

**Key existing facts (verified):**
- `src/api/content.ts`: `ModuleOut{id,title,icon,order_index,locked}`, `LevelOut{id,order_index,state:'in_progress'|'completed'|'locked',locked_reason,lessons_total,lessons_completed}`, `LessonSummary{id,type,title,order_index,completed}`. `contentApi.listModules()`, `contentApi.listLevels(moduleId)`, `contentApi.listLevelLessons(levelId)`.
- `src/api/ai.ts`: `useRecommendations()` → `CategorisedRecommendations{continue_learning:[{module_id,...}],something_new:[...],review_summary:{due_count}}`. `aiApi` object + hooks live here.
- `src/hooks/useChildSession.ts` → `Me{username,is_premium}`.
- Eddie avatar in-app is the 💡 emoji (see `EddieFAB.tsx`).
- Backend `app/routers/ai.py` is `APIRouter(tags=["ai"])`; `app/services/coach_service.coach_chat` shows the LLM+moderation pattern: `get_llm_client(tier="premium" if premium else "standard")`, `get_model_name(...)`, `await moderate_output(raw_response, surface="tutor")` (lines ~262–271). `is_premium` from `app.services.entitlements`.

## File Structure

Frontend:
- Create `src/lib/homeHero.ts` — pure `pickTargetModule`, `pickTargetLevel`, `pickTargetLesson`, `buildHeroGreeting`.
- Create `src/lib/__tests__/homeHero.test.ts`.
- Create `src/hooks/useNextLesson.ts`.
- Create `src/components/child/HomeHero.tsx` + `src/components/child/__tests__/HomeHero.test.tsx`.
- Modify `src/api/ai.ts` — `homeGreeting` call + `useHomeGreeting` hook + types.
- Modify `src/pages/child/Home.tsx` — render `HomeHero`, drop empty-state box.

Backend:
- Modify `app/schemas/ai.py` — `HomeGreetingRequest`, `HomeGreetingResponse`.
- Create `app/services/home_greeting_service.py`.
- Modify `app/routers/ai.py` — `POST /home-greeting`.
- Create `tests/test_home_greeting.py`.

---

### Task 1: Pure helpers + tests (`src/lib/homeHero.ts`)

**Files:** Create `src/lib/homeHero.ts`, `src/lib/__tests__/homeHero.test.ts`.

- [ ] **Step 1: Write the failing tests** — `src/lib/__tests__/homeHero.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { pickTargetModule, pickTargetLevel, pickTargetLesson, buildHeroGreeting } from '@/lib/homeHero';
import type { ModuleOut, LevelOut, LessonSummary } from '@/api/content';

const mod = (id: string, order: number, locked = false): ModuleOut => ({
  id, topic: 'stocks', title: `M${id}`, country_codes: [], is_premium: false, order_index: order, icon: '📈', locked,
});

describe('pickTargetModule', () => {
  it('prefers continue_learning', () => {
    const r = pickTargetModule({ continue_learning: [{ module_id: 'c' }], something_new: [{ module_id: 'n' }] } as never, [mod('a', 0)]);
    expect(r).toEqual({ moduleId: 'c', mode: 'continue' });
  });
  it('falls back to something_new', () => {
    const r = pickTargetModule({ continue_learning: [], something_new: [{ module_id: 'n' }] } as never, [mod('a', 0)]);
    expect(r).toEqual({ moduleId: 'n', mode: 'start' });
  });
  it('falls back to first unlocked module by order', () => {
    const r = pickTargetModule({ continue_learning: [], something_new: [] } as never, [mod('b', 2), mod('a', 1), mod('locked', 0, true)]);
    expect(r).toEqual({ moduleId: 'a', mode: 'start' });
  });
  it('returns null when nothing available', () => {
    expect(pickTargetModule(null, [mod('x', 0, true)])).toBeNull();
  });
});

const lvl = (id: string, order: number, state: LevelOut['state'], done: number, total: number): LevelOut => ({
  id, module_id: 'm', title: id, order_index: order, is_premium: false, icon: '📊', state, locked_reason: null, passed: false, lessons_total: total, lessons_completed: done,
});

describe('pickTargetLevel', () => {
  it('returns first unlocked, not-complete level by order', () => {
    const r = pickTargetLevel([lvl('l2', 1, 'in_progress', 0, 3), lvl('l1', 0, 'completed', 3, 3)]);
    expect(r?.id).toBe('l2');
  });
  it('skips locked levels', () => {
    const r = pickTargetLevel([lvl('l1', 0, 'locked', 0, 3)]);
    expect(r).toBeNull();
  });
  it('returns null when all complete', () => {
    expect(pickTargetLevel([lvl('l1', 0, 'completed', 3, 3)])).toBeNull();
  });
});

const lsn = (id: string, order: number, completed: boolean): LessonSummary => ({
  id, type: 'quiz', title: `L${id}`, xp_reward: 10, order_index: order, completed,
});

describe('pickTargetLesson', () => {
  it('returns first incomplete lesson by order', () => {
    const r = pickTargetLesson([lsn('b', 1, false), lsn('a', 0, true)]);
    expect(r?.id).toBe('b');
  });
  it('returns null when all complete', () => {
    expect(pickTargetLesson([lsn('a', 0, true)])).toBeNull();
  });
});

describe('buildHeroGreeting', () => {
  it('start mode names the lesson', () => {
    expect(buildHeroGreeting({ name: 'Sam', mode: 'start', lessonLabel: 'What is a Stock?', streakCount: 0, dueCount: 0 }))
      .toContain('What is a Stock?');
  });
  it('continue mode welcomes back', () => {
    expect(buildHeroGreeting({ name: 'Sam', mode: 'continue', lessonLabel: 'Compound Interest', streakCount: 3, dueCount: 0 }))
      .toMatch(/Welcome back, Sam/);
  });
  it('reviews due takes priority', () => {
    expect(buildHeroGreeting({ name: 'Sam', mode: 'start', lessonLabel: 'X', streakCount: 0, dueCount: 2 }))
      .toContain('2 concepts');
  });
  it('caught_up celebrates', () => {
    expect(buildHeroGreeting({ name: 'Sam', mode: 'caught_up', lessonLabel: null, streakCount: 0, dueCount: 0 }))
      .toMatch(/finished everything/);
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `npx vitest run src/lib/__tests__/homeHero.test.ts` → FAIL (module not found).

- [ ] **Step 3: Implement** — `src/lib/homeHero.ts`:

```ts
import type { ModuleOut, LevelOut, LessonSummary } from '@/api/content';
import type { CategorisedRecommendations } from '@/api/ai';

export type HeroMode = 'start' | 'continue' | 'caught_up';

export interface TargetModule {
  moduleId: string;
  mode: 'start' | 'continue';
}

export function pickTargetModule(
  recs: CategorisedRecommendations | null | undefined,
  modules: ModuleOut[],
): TargetModule | null {
  const cont = recs?.continue_learning?.[0];
  if (cont) return { moduleId: cont.module_id, mode: 'continue' };
  const fresh = recs?.something_new?.[0];
  if (fresh) return { moduleId: fresh.module_id, mode: 'start' };
  const unlocked = modules.filter((m) => !m.locked).sort((a, b) => a.order_index - b.order_index);
  return unlocked.length > 0 ? { moduleId: unlocked[0].id, mode: 'start' } : null;
}

export function pickTargetLevel(levels: LevelOut[]): LevelOut | null {
  return [...levels]
    .sort((a, b) => a.order_index - b.order_index)
    .find((l) => l.state !== 'locked' && l.lessons_completed < l.lessons_total) ?? null;
}

export function pickTargetLesson(lessons: LessonSummary[]): LessonSummary | null {
  return [...lessons].sort((a, b) => a.order_index - b.order_index).find((l) => !l.completed) ?? null;
}

export interface HeroGreetingCtx {
  name: string;
  mode: HeroMode;
  lessonLabel: string | null;
  streakCount: number;
  dueCount: number;
}

export function buildHeroGreeting(ctx: HeroGreetingCtx): string {
  const name = ctx.name || 'there';
  if (ctx.dueCount > 0) {
    const plural = ctx.dueCount === 1 ? 'concept' : 'concepts';
    return `Welcome back, ${name}! You've got ${ctx.dueCount} ${plural} ready to review. 🧠`;
  }
  if (ctx.mode === 'caught_up') {
    return `Amazing work, ${name}! You've finished everything for now. 🎉 New quests coming soon!`;
  }
  if (ctx.mode === 'continue') {
    const streak = ctx.streakCount > 1 ? ` ${ctx.streakCount}-day streak — keep it going!` : '';
    return `Welcome back, ${name}!${streak} Let's pick up ${ctx.lessonLabel ?? 'your next quest'}.`;
  }
  return `Let's start your money journey, ${name}! First up: ${ctx.lessonLabel ?? 'your first lesson'} 📈`;
}
```

- [ ] **Step 4: Run to verify pass** — `npx vitest run src/lib/__tests__/homeHero.test.ts` → all pass. Then `npx tsc -b` clean.

- [ ] **Step 5: Commit**
```bash
git add invest-ed/frontend/src/lib/homeHero.ts invest-ed/frontend/src/lib/__tests__/homeHero.test.ts
git commit -m "feat(home): pure next-lesson resolver + templated greeting builder

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `useNextLesson` hook

**Files:** Create `src/hooks/useNextLesson.ts`.

- [ ] **Step 1: Implement the hook**

```ts
import { useQuery } from '@tanstack/react-query';
import { contentApi, type ModuleOut, type LevelOut, type LessonSummary } from '@/api/content';
import { useRecommendations } from '@/api/ai';
import { pickTargetModule, pickTargetLevel, pickTargetLesson, type HeroMode } from '@/lib/homeHero';

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
  const { data: recs, isLoading: recsLoading } = useRecommendations();
  const modulesQ = useQuery<ModuleOut[] | null>({
    queryKey: ['modules'], queryFn: () => contentApi.listModules(), retry: false, staleTime: 60_000,
  });
  const modules = modulesQ.data ?? [];

  const target = pickTargetModule(recs, modules);
  const moduleId = target?.moduleId ?? null;
  const module = modules.find((m) => m.id === moduleId) ?? null;

  const levelsQ = useQuery<LevelOut[] | null>({
    queryKey: ['module-levels', moduleId], queryFn: () => contentApi.listLevels(moduleId!),
    enabled: !!moduleId, retry: false, staleTime: 60_000,
  });
  const targetLevel = levelsQ.data ? pickTargetLevel(levelsQ.data) : null;

  const lessonsQ = useQuery<LessonSummary[] | null>({
    queryKey: ['level-lessons', targetLevel?.id], queryFn: () => contentApi.listLevelLessons(targetLevel!.id),
    enabled: !!targetLevel, retry: false, staleTime: 60_000,
  });
  const targetLesson = lessonsQ.data ? pickTargetLesson(lessonsQ.data) : null;

  const isLoading = recsLoading || modulesQ.isLoading
    || (!!moduleId && levelsQ.isLoading)
    || (!!targetLevel && lessonsQ.isLoading);

  // caught_up: a module was found but it has no unlocked, incomplete level,
  // or the chosen level has no incomplete lesson; or no module at all.
  const caughtUp = !isLoading && (
    target === null
    || (!!levelsQ.data && targetLevel === null)
    || (!!lessonsQ.data && targetLesson === null)
  );

  if (caughtUp) {
    return { mode: 'caught_up', moduleId: null, levelId: null, lessonId: null, moduleTitle: null, moduleIcon: null, lessonLabel: null, to: null, isLoading: false };
  }

  if (!target || !targetLevel || !targetLesson || !module) {
    return { mode: target?.mode ?? 'start', moduleId, levelId: targetLevel?.id ?? null, lessonId: null, moduleTitle: module?.title ?? null, moduleIcon: module?.icon ?? null, lessonLabel: null, to: null, isLoading };
  }

  return {
    mode: target.mode,
    moduleId, levelId: targetLevel.id, lessonId: targetLesson.id,
    moduleTitle: module.title, moduleIcon: module.icon, lessonLabel: targetLesson.title,
    to: `/lessons/${moduleId}/${targetLevel.id}/${targetLesson.id}`,
    isLoading: false,
  };
}
```

- [ ] **Step 2: Typecheck** — `npx tsc -b` clean.

- [ ] **Step 3: Commit**
```bash
git add invest-ed/frontend/src/hooks/useNextLesson.ts
git commit -m "feat(home): useNextLesson hook resolving the next lesson target

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Backend AI greeting schemas + service

**Files:** Modify `app/schemas/ai.py`; Create `app/services/home_greeting_service.py`.

- [ ] **Step 1: Add schemas** to `app/schemas/ai.py` (file already imports `BaseModel`):

```python
class HomeGreetingRequest(BaseModel):
    name: str = ""
    mode: str  # "start" | "continue" | "caught_up"
    lesson_label: str | None = None
    streak_count: int = 0
    due_count: int = 0


class HomeGreetingResponse(BaseModel):
    greeting: str
```

- [ ] **Step 2: Implement the service** — `app/services/home_greeting_service.py`. Mirror the LLM+moderation call in `app/services/coach_service.coach_chat` (open it and copy the exact `get_llm_client` / completion call / `moderate_output` usage — do NOT guess the client method name; use whatever `coach_chat` uses):

```python
from app.services.llm_client import get_llm_client, get_model_name
from app.services.moderation import moderate_output

_MAX_LEN = 160


def _build_messages(*, name: str, mode: str, lesson_label: str | None, streak_count: int, due_count: int) -> list[dict]:
    context = (
        f"Child's name: {name or 'there'}. Mode: {mode}. "
        f"Next lesson: {lesson_label or 'n/a'}. Streak: {streak_count} days. "
        f"Concepts due for review: {due_count}."
    )
    system = (
        "You are Coach Eddie, a warm, encouraging money-skills buddy for a child. "
        "Write ONE short, upbeat greeting (max 20 words) for the home screen that nudges "
        "them toward their next lesson. Friendly, age-appropriate, no emojis spam (at most one). "
        "Do not give financial advice. Output only the greeting text."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": context},
    ]


async def generate_home_greeting(*, name: str, mode: str, lesson_label: str | None, streak_count: int, due_count: int) -> str:
    """Premium AI greeting. Raises on provider/moderation failure so the caller
    can fall back to the client-side templated line."""
    client = get_llm_client(tier="premium")
    model_name = get_model_name("premium")
    messages = _build_messages(name=name, mode=mode, lesson_label=lesson_label, streak_count=streak_count, due_count=due_count)

    # NOTE: replicate the exact completion call used in coach_service.coach_chat.
    raw = await client.complete(model=model_name, messages=messages, max_tokens=60)
    text = (raw or "").strip().strip('"')[:_MAX_LEN]
    if not text:
        raise ValueError("empty greeting")

    mod = await moderate_output(text, surface="coach")
    if not getattr(mod, "allowed", True):
        raise ValueError("greeting blocked by moderation")
    return text
```
Adjust `client.complete(...)` and the `moderate_output` return-handling to EXACTLY match `coach_chat` (e.g. if it unpacks `_mod` differently). Run `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/home_greeting_service.py app/schemas/ai.py` → pass.

- [ ] **Step 3: Commit**
```bash
git add invest-ed/backend/app/schemas/ai.py invest-ed/backend/app/services/home_greeting_service.py
git commit -m "feat(home): premium home-greeting LLM service + schemas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `POST /ai/home-greeting` endpoint + tests

**Files:** Modify `app/routers/ai.py`; Create `tests/test_home_greeting.py`.

- [ ] **Step 1: Write failing tests** — `tests/test_home_greeting.py`. First open an existing Coach Eddie endpoint test (find via `grep -rl "tutor/coach" tests/`) and copy how it (a) builds an authenticated premium user and a non-premium user and (b) patches the LLM client + `moderate_output`. Then:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

_BODY = {"name": "Sam", "mode": "start", "lesson_label": "What is a Stock?", "streak_count": 0, "due_count": 0}


async def test_home_greeting_premium_returns_greeting(<PREMIUM_CLIENT>, monkeypatch):
    async def fake_gen(**kwargs):
        return "Let's go, Sam!"
    monkeypatch.setattr("app.routers.ai.generate_home_greeting", fake_gen)
    r = await <PREMIUM_CLIENT>.post("/home-greeting", json=_BODY)
    assert r.status_code == 200
    assert r.json()["greeting"] == "Let's go, Sam!"


async def test_home_greeting_non_premium_403(<FREE_CLIENT>):
    r = await <FREE_CLIENT>.post("/home-greeting", json=_BODY)
    assert r.status_code == 403


async def test_home_greeting_provider_failure_503(<PREMIUM_CLIENT>, monkeypatch):
    async def boom(**kwargs):
        raise RuntimeError("provider down")
    monkeypatch.setattr("app.routers.ai.generate_home_greeting", boom)
    r = await <PREMIUM_CLIENT>.post("/home-greeting", json=_BODY)
    assert r.status_code == 503
```
Replace `<PREMIUM_CLIENT>` / `<FREE_CLIENT>` with the real fixtures/helpers from the coach test (e.g. a client whose user has been made premium vs a default free user). Do not invent fixtures.

- [ ] **Step 2: Run to verify it fails** — `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_home_greeting.py -q` → FAIL (route missing).

- [ ] **Step 3: Implement** — in `app/routers/ai.py`: add to the `app.schemas.ai` import `HomeGreetingRequest, HomeGreetingResponse`, add `from app.services.home_greeting_service import generate_home_greeting`, and add:

```python
@router.post("/home-greeting", response_model=HomeGreetingResponse)
async def home_greeting(
    payload: HomeGreetingRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not is_premium(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Premium required")
    try:
        text = await generate_home_greeting(
            name=current_user.username or payload.name,
            mode=payload.mode,
            lesson_label=payload.lesson_label,
            streak_count=payload.streak_count,
            due_count=payload.due_count,
        )
    except Exception as exc:  # provider error or moderation block → client falls back to templated line
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Greeting unavailable") from exc
    return HomeGreetingResponse(greeting=text)
```
(`is_premium`, `status`, `HTTPException`, `Depends`, `get_current_user`, `get_session`, `User`, `AsyncSession` are already imported in this router — verify.)

- [ ] **Step 4: Run to verify pass** — `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_home_greeting.py -q` → 3 passed. Then `ruff check app/routers/ai.py tests/test_home_greeting.py` → pass.

- [ ] **Step 5: Commit**
```bash
git add invest-ed/backend/app/routers/ai.py invest-ed/backend/tests/test_home_greeting.py
git commit -m "feat(home): premium-gated home-greeting endpoint + tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Frontend AI greeting API + hook

**Files:** Modify `src/api/ai.ts`.

- [ ] **Step 1: Add the call + types + hook** in `src/api/ai.ts`:

Add types:
```ts
export type HomeGreetingCtxBody = {
  name: string;
  mode: 'start' | 'continue' | 'caught_up';
  lesson_label: string | null;
  streak_count: number;
  due_count: number;
};
export type HomeGreetingResponse = { greeting: string };
```
Add to the `aiApi` object:
```ts
  homeGreeting: (body: HomeGreetingCtxBody) =>
    apiFetch<HomeGreetingResponse>('/home-greeting', { method: 'POST', body: JSON.stringify(body) }),
```
Add a hook (match the file's existing `useQuery` hook style):
```ts
export function useHomeGreeting(body: HomeGreetingCtxBody, enabled: boolean) {
  return useQuery({
    queryKey: ['home-greeting', body.mode, body.lesson_label, body.streak_count, body.due_count, body.name],
    queryFn: () => aiApi.homeGreeting(body),
    enabled,
    staleTime: Infinity,
    retry: false,
  });
}
```

- [ ] **Step 2: Typecheck** — `npx tsc -b` clean.

- [ ] **Step 3: Commit**
```bash
git add invest-ed/frontend/src/api/ai.ts
git commit -m "feat(home): home-greeting API call + useHomeGreeting hook (premium)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `HomeHero` component + tests

**Files:** Create `src/components/child/HomeHero.tsx`, `src/components/child/__tests__/HomeHero.test.tsx`.

- [ ] **Step 1: Write the failing test** — `src/components/child/__tests__/HomeHero.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import HomeHero from '../HomeHero';

const next = {
  mode: 'start' as const, moduleId: 'm1', levelId: 'l1', lessonId: 'q1',
  moduleTitle: 'Stocks', moduleIcon: '📈', lessonLabel: 'What is a Stock?',
  to: '/lessons/m1/l1/q1', isLoading: false,
};

vi.mock('@/hooks/useNextLesson', () => ({ useNextLesson: () => next }));
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: () => ({ data: { username: 'Sam', is_premium: false } }) }));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({ data: { review_summary: { due_count: 0 } } }),
  useHomeGreeting: () => ({ data: undefined }),
}));
vi.mock('@/hooks/useProgress', () => ({ useProgress: () => ({ data: { streak_count: 0 } }) }));

function wrap(ui: React.ReactNode) { return <MemoryRouter>{ui}</MemoryRouter>; }

describe('HomeHero', () => {
  it('shows the templated greeting, lesson title and a Start link', () => {
    render(wrap(<HomeHero />));
    expect(screen.getByText(/start your money journey/i)).toBeInTheDocument();
    expect(screen.getByText('What is a Stock?')).toBeInTheDocument();
    const cta = screen.getByRole('link', { name: /start/i });
    expect(cta).toHaveAttribute('href', '/lessons/m1/l1/q1');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<HomeHero />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `npx vitest run src/components/child/__tests__/HomeHero.test.tsx` → FAIL (no component).

- [ ] **Step 3: Implement** — `src/components/child/HomeHero.tsx`:

```tsx
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useNextLesson } from '@/hooks/useNextLesson';
import { useChildSession } from '@/hooks/useChildSession';
import { useProgress } from '@/hooks/useProgress';
import { useRecommendations, useHomeGreeting } from '@/api/ai';
import { buildHeroGreeting } from '@/lib/homeHero';

export default function HomeHero() {
  const next = useNextLesson();
  const { data: me } = useChildSession();
  const { data: progress } = useProgress();
  const { data: recs } = useRecommendations();

  const name = me?.username ?? 'there';
  const streakCount = progress?.streak_count ?? 0;
  const dueCount = recs?.review_summary?.due_count ?? 0;
  const isPremium = me?.is_premium ?? false;

  const templated = buildHeroGreeting({ name, mode: next.mode, lessonLabel: next.lessonLabel, streakCount, dueCount });

  // Premium: progressively swap in the moderated AI line when it arrives.
  const aiQ = useHomeGreeting(
    { name, mode: next.mode, lesson_label: next.lessonLabel, streak_count: streakCount, due_count: dueCount },
    isPremium && !next.isLoading,
  );
  const greeting = (isPremium && aiQ.data?.greeting) ? aiQ.data.greeting : templated;

  const ctaLabel = next.mode === 'continue' ? 'Continue' : 'Start';

  return (
    <section aria-labelledby="home-hero-greeting" className="mb-2">
      {/* Eddie + speech bubble */}
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-amber-100 text-2xl shadow" aria-hidden="true">💡</div>
        <motion.p
          id="home-hero-greeting"
          className="rounded-2xl rounded-tl-sm border border-amber-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-800 shadow-sm"
          initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
        >
          {greeting}
        </motion.p>
      </div>

      {/* Hero action card */}
      <motion.div
        className="mt-3 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 p-5 text-white shadow-lg"
        initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.35, delay: 0.05 }}
      >
        {next.isLoading ? (
          <div className="h-16 animate-pulse rounded-xl bg-white/30" aria-hidden="true" />
        ) : next.mode === 'caught_up' || !next.to ? (
          <div>
            <p className="text-xs font-bold uppercase tracking-wider opacity-90">🎉 All caught up</p>
            <p className="mt-1 text-lg font-extrabold">You've finished everything for now!</p>
            <Link to={dueCount > 0 ? '/progress' : '/lessons'}
              className="mt-3 inline-block rounded-xl bg-white px-5 py-2.5 text-sm font-extrabold text-amber-700 shadow">
              {dueCount > 0 ? 'Review concepts →' : 'Explore modules →'}
            </Link>
          </div>
        ) : (
          <div>
            <p className="text-xs font-bold uppercase tracking-wider opacity-90">▶ {ctaLabel === 'Continue' ? 'Pick up where you left off' : 'Start here'}</p>
            <p className="mt-1 text-lg font-extrabold leading-tight">
              <span aria-hidden="true">{next.moduleIcon} </span>{next.lessonLabel}
            </p>
            <Link to={next.to}
              className="mt-3 inline-block rounded-xl bg-white px-5 py-2.5 text-sm font-extrabold text-amber-700 shadow hover:bg-amber-50">
              {ctaLabel} →
            </Link>
          </div>
        )}
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 4: Run to verify pass** — `npx vitest run src/components/child/__tests__/HomeHero.test.tsx` → 2 passed. Fix any axe violations by adjusting markup (don't weaken the test). Then `npx tsc -b` clean, `npm run lint` clean (only pre-existing warning).

- [ ] **Step 5: Commit**
```bash
git add invest-ed/frontend/src/components/child/HomeHero.tsx invest-ed/frontend/src/components/child/__tests__/HomeHero.test.tsx
git commit -m "feat(home): Eddie-led HomeHero with templated-first, premium AI swap

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Wire `HomeHero` into the home page

**Files:** Modify `src/pages/child/Home.tsx`; update its test if one exists.

- [ ] **Step 1: Render the hero, drop the empty-state box** — in `src/pages/child/Home.tsx`:
  - Add `import HomeHero from '@/components/child/HomeHero';`
  - Replace the greeting block (`<h1>Hey {username}…</h1>` + the "Ready to level up…" `<p>`) with `<HomeHero />` at the top of the returned container (the hero now carries the greeting). To preserve heading order (the recommendation sections use `<h2>`), keep a screen-reader-only page heading just above the hero: `<h1 className="sr-only">Your learning home</h1>`.
  - In the recommendations area, REMOVE the empty-state `else` branch (the `<section>` with "Complete a lesson to get personalised recommendations!"). When there are no recommendations, render nothing there — the hero already gives the next action. Keep the `recsLoading` and `hasAnything` branches.
  - Keep `StatsBar`, the XP bar, `ReviewBanner`, the `CategorySection`s, and the "Browse all modules" button below.

- [ ] **Step 2: Update the Home page test if present** — check `grep -rl "Home" src/**/__tests__ tests 2>/dev/null` for a Home page test. If one renders the empty-state text or the old `<h1>`, update it: mock `@/hooks/useNextLesson` and `@/api/ai`'s `useHomeGreeting` (as in Task 6), and assert the hero renders instead of the removed copy. If there is no Home page test, skip.

- [ ] **Step 3: Verify** — `npx tsc -b` clean; `npm run lint` clean (only pre-existing warning); `npx vitest run` for any touched test → pass.

- [ ] **Step 4: Commit**
```bash
git add invest-ed/frontend/src/pages/child/Home.tsx
# plus the Home test file if you modified it
git commit -m "feat(home): lead the child home with HomeHero; remove empty state

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Full regression + close-out

**Files:** none (verification only)

- [ ] **Step 1: Backend** — `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_home_greeting.py -q` (and the broader suite if the local Postgres is healthy; otherwise rely on CI).
- [ ] **Step 2: Frontend** — `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`. Expected: tsc clean; lint only the pre-existing `button.tsx` warning; all vitest tests pass; build OK.
- [ ] **Step 3: iOS sync** — `npx cap sync ios` (the home redesign ships in the web bundle; the child app needs a rebuild to show it).
- [ ] **Step 4: Push + CI** — `git push origin main`; confirm all 5 CI jobs pass before considering it deployed.
- [ ] **Step 5: Final review** — dispatch a final code review across the feature; address any blocking findings.

## Notes for the implementer
- The templated line must ALWAYS render first; the AI line is a progressive enhancement for premium only and must never block or blank the hero.
- Don't add a maximum-scale viewport or otherwise regress the iOS input-zoom / overflow fixes.
- Keep the existing StatsBar / XP bar / ReviewBanner / recommendation sections — this feature only adds the hero and removes the empty-state box.
- Backend LLM/moderation calls must match `coach_service.coach_chat` exactly (client method, `moderate_output` handling) — copy, don't guess.
