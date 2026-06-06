# Age-Tier Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt tone/copy, mascot prominence, and module ordering to a DOB-derived age tier (explorer 10–13 / investor 14–18) that is always computed live, never stored.

**Architecture:** A pure backend helper derives the tier from `User.dob`; a `User.age_tier` property exposes it on the `Me` response (`from_attributes`) and feeds the LLM register directives. The frontend reads `me.age_tier` and drives templated copy, Penny size, and module ordering from centralized config modules.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2; React 18 + Vite + TS + TanStack Query + Vitest/vitest-axe.

**Spec:** `docs/superpowers/specs/2026-06-05-age-tier-mode-design.md`

**Working dirs:** backend `invest-ed/backend`, frontend `invest-ed/frontend`. Git from repo root; commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

**Commands:** Backend `/Users/leeashmore/Local\ Repo/.venv/bin/pytest` · `ruff check .`. Frontend `npx tsc -b` · `npm run lint` (known `button.tsx`/`Market.tsx` warnings OK) · `npm test` · `npm run build`.

**Notes:** Async backend tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session`. Local Postgres can hang → rely on CI. NEVER touch `.env*` (a pre-existing unstaged `.env.production` exists). A parallel `tests/unit/` FE mirror exists — run the FULL `npm test` after FE changes. No DB migration in this plan (tier is computed, not stored). **Consent note:** a child under 13 (GB/COPPA) registers as *pending consent* (inactive, can't log in), so integration tests that hit `/users/me` must use an age ≥14 (investor) user; cover the explorer tier via pure unit tests on the helper + the `User.age_tier` property.

## File Structure

**Backend**
- Create `app/services/age_tier.py` — `AGE_TIER_BOUNDARY`, `AgeTier` type, `age_in_years`, `age_tier`, and `AGE_REGISTER_DIRECTIVE` (the LLM tone directives — single source).
- Modify `app/models/user.py` — `User.age_tier` property.
- Modify `app/schemas/user.py` — `UserProfile.age_tier`.
- Modify `app/services/home_greeting_service.py` + `app/routers/ai.py` — thread tier into the greeting prompt.
- Modify `app/services/coach_service.py` — append the register directive from `user.age_tier`.

**Frontend**
- Modify `src/api/auth.ts` — `Me.age_tier`.
- Create `src/lib/ageTier.ts` — `AgeTier`, `tierConfig` (mascot knobs), `useAgeTier()`.
- Create `src/lib/tierCopy.ts` — `HERO_GREETING` + `ENCOURAGEMENT` per-tier copy.
- Create `src/lib/tierModuleOrder.ts` — `orderModulesForTier`.
- Modify `src/lib/homeHero.ts` (tier-aware `buildHeroGreeting`), `src/components/child/HomeHero.tsx` (greeting + Penny size), `src/components/child/lesson/LessonChrome.tsx` (tier encouragement), `src/pages/child/Home.tsx` + `src/pages/child/Lessons.tsx` (module ordering).

---

### Task 1: Backend tier derivation + expose on `Me`

**Files:** Create `app/services/age_tier.py`; Modify `app/models/user.py`, `app/schemas/user.py`; Test `tests/test_age_tier.py` (new).

- [ ] **Step 1: Write the failing tests** — create `tests/test_age_tier.py`:

```python
from datetime import date

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_age_tier_boundary():
    from app.services.age_tier import AGE_TIER_BOUNDARY, age_tier
    assert AGE_TIER_BOUNDARY == 14
    today = date(2026, 6, 6)
    assert age_tier(date(2016, 1, 1), today) == "explorer"   # age 10
    assert age_tier(date(2013, 1, 1), today) == "explorer"   # age 13
    assert age_tier(date(2012, 1, 1), today) == "investor"   # age 14
    assert age_tier(date(2009, 1, 1), today) == "investor"   # age 17
    # birthday not yet reached this year
    assert age_tier(date(2012, 12, 31), today) == "explorer"  # still 13 on 2026-06-06


def test_user_age_tier_property():
    from app.models.user import User
    explorer = User(username="x", password_hash="x", dob=date(2015, 1, 1), country_code="GB", currency_code="GBP")
    investor = User(username="y", password_hash="x", dob=date(2010, 1, 1), country_code="GB", currency_code="GBP")
    assert explorer.age_tier == "explorer"
    assert investor.age_tier == "investor"


async def test_me_exposes_age_tier_for_investor(client, db_session):
    # A 15-year-old (>=14, and not under the GB consent age) can register + log in.
    await client.post("/auth/register", json={
        "email": "teen@example.com", "username": "teen", "password": "SecurePass123!",
        "dob": "2011-01-01", "country_code": "GB", "currency_code": "GBP",
    })
    r = await client.get("/users/me")
    assert r.status_code == 200
    assert r.json()["age_tier"] == "investor"
```
(If the `User(...)` kwargs don't match the model, READ `app/models/user.py` and adjust to the real required fields — keep assertions intact. If a 2011 DOB still triggers GB parental consent in this codebase, READ `app/schemas/auth.py`/`compliance.py` for the threshold and pick the youngest age that both is `investor` and does NOT require consent; if every minor requires consent, replace the integration test with a direct `UserProfile.model_validate(user_obj)` assertion instead.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_age_tier.py -v`
Expected: FAIL — `age_tier` module / `User.age_tier` / schema field missing.

- [ ] **Step 3: Create `app/services/age_tier.py`**

```python
"""Single source of truth for the age-tier (derived live from DOB; never stored)."""
from datetime import date
from typing import Literal

AGE_TIER_BOUNDARY = 14  # age (inclusive) at which a learner becomes "investor"

AgeTier = Literal["explorer", "investor"]


def age_in_years(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def age_tier(dob: date, today: date) -> AgeTier:
    return "investor" if age_in_years(dob, today) >= AGE_TIER_BOUNDARY else "explorer"


# LLM register directives — the ONE place to retune tone per tier.
AGE_REGISTER_DIRECTIVE: dict[AgeTier, str] = {
    "explorer": (
        "The learner is 10-13. Be warm, playful, simple and encouraging; "
        "at most one light emoji; avoid jargon."
    ),
    "investor": (
        "The learner is 14-18. Be encouraging but mature and concise; no baby-talk; "
        "minimal or no emoji; you may use real financial terms."
    ),
}
```

- [ ] **Step 4: Add the `User.age_tier` property** — in `app/models/user.py`, add the import (top, with the other imports; `date` is already imported) and a property on the `User` class:

```python
from app.services.age_tier import age_tier as _age_tier
```
```python
    @property
    def age_tier(self) -> str:
        """Live age tier derived from dob (never stored)."""
        return _age_tier(self.dob, date.today())
```
(If importing the service at module top causes a circular import, move the `from app.services.age_tier import age_tier as _age_tier` inside the property body instead.)

- [ ] **Step 5: Add the schema field** — in `app/schemas/user.py`, add to `UserProfile` (it already has `model_config = {"from_attributes": True}`, so the property auto-populates):

```python
from app.services.age_tier import AgeTier
```
```python
    age_tier: AgeTier = "explorer"
```
(Place the field among the other `UserProfile` fields.)

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_age_tier.py -v`
Expected: PASS.

- [ ] **Step 7: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/age_tier.py invest-ed/backend/app/models/user.py invest-ed/backend/app/schemas/user.py invest-ed/backend/tests/test_age_tier.py
git commit -m "feat: derive + expose live age_tier on the user profile

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Tier-aware LLM register (greeting + coach)

**Files:** Modify `app/services/home_greeting_service.py`, `app/routers/ai.py`, `app/services/coach_service.py`; Test `tests/test_age_tier.py`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_age_tier.py`:

```python
def test_age_register_directive_has_both_tiers():
    from app.services.age_tier import AGE_REGISTER_DIRECTIVE
    assert "10-13" in AGE_REGISTER_DIRECTIVE["explorer"]
    assert "14-18" in AGE_REGISTER_DIRECTIVE["investor"]
    assert AGE_REGISTER_DIRECTIVE["explorer"] != AGE_REGISTER_DIRECTIVE["investor"]


def test_home_greeting_prompt_includes_tier_directive():
    from app.services.age_tier import AGE_REGISTER_DIRECTIVE
    from app.services.home_greeting_service import _build_messages

    sys_e, _ = _build_messages(name="A", mode="start", lesson_label="L", streak_count=0, due_count=0, tier="explorer")
    sys_i, _ = _build_messages(name="A", mode="start", lesson_label="L", streak_count=0, due_count=0, tier="investor")
    assert AGE_REGISTER_DIRECTIVE["explorer"] in sys_e
    assert AGE_REGISTER_DIRECTIVE["investor"] in sys_i
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_age_tier.py -k "directive or greeting_prompt" -v`
Expected: FAIL — `_build_messages` has no `tier` param.

- [ ] **Step 3: Thread tier into `home_greeting_service.py`** — add the import and a `tier` parameter to both functions:

```python
from app.services.age_tier import AGE_REGISTER_DIRECTIVE, AgeTier
```
In `_build_messages`, add `tier: AgeTier` to the keyword-only params and append the directive to the system prompt:
```python
def _build_messages(
    *,
    name: str,
    mode: str,
    lesson_label: str | None,
    streak_count: int,
    due_count: int,
    tier: AgeTier,
) -> tuple[str, list[dict]]:
    system_prompt = (
        "You are Coach Penny, a warm, encouraging piggy-bank money-skills buddy for a child. "
        "Write ONE short, upbeat greeting (max 20 words) for the home screen that nudges "
        "them toward their next lesson. Friendly, age-appropriate, at most one emoji. "
        "Do not give financial advice. Output only the greeting text. "
        + AGE_REGISTER_DIRECTIVE[tier]
    )
    ...
```
In `generate_home_greeting`, add `tier: AgeTier` to the keyword-only params and pass it through to `_build_messages(..., tier=tier)`.

- [ ] **Step 4: Pass the tier from the endpoint** — in `app/routers/ai.py`, the `home_greeting` handler (~line 177) calls `generate_home_greeting(...)`. Add `tier=current_user.age_tier` to that call.

- [ ] **Step 5: Append the directive in `coach_service.py`** — add the import and, immediately after the existing `system_prompt = _COACH_SYSTEM_PROMPT.format(...)` (~line 249), append the directive from the authenticated `user`:

```python
from app.services.age_tier import AGE_REGISTER_DIRECTIVE
```
```python
    system_prompt = _COACH_SYSTEM_PROMPT.format(
        skill_level_instruction=_SKILL_INSTRUCTIONS[level],
        learning_state_context=context_block,
    )
    system_prompt = f"{system_prompt}\n\n{AGE_REGISTER_DIRECTIVE[user.age_tier]}"
```
(`coach_chat` already receives `user: User`, so no signature change — just read `user.age_tier`.)

- [ ] **Step 6: Run the new tests + the existing AI/coach/greeting tests**

Run:
```
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_age_tier.py -v && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -k "greeting or coach or tutor" -q
```
Expected: PASS. If a greeting test calls `_build_messages`/`generate_home_greeting` without `tier`, update it to pass a tier (don't weaken it).

- [ ] **Step 7: Lint + commit**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/home_greeting_service.py invest-ed/backend/app/routers/ai.py invest-ed/backend/app/services/coach_service.py invest-ed/backend/tests/test_age_tier.py
git commit -m "feat: inject age-tier register directive into greeting + coach prompts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: FE tier foundations + tier-aware hero greeting copy

**Files:** Modify `src/api/auth.ts`, `src/lib/homeHero.ts`; Create `src/lib/ageTier.ts`, `src/lib/tierCopy.ts`; Test `src/lib/__tests__/tierCopy.test.ts` (new).

- [ ] **Step 1: Add the FE type** — in `src/api/auth.ts`, add to the `Me` type: `age_tier: 'explorer' | 'investor';`.

- [ ] **Step 2: Create `src/lib/ageTier.ts`**

```ts
import { useChildSession } from '@/hooks/useChildSession';

export type AgeTier = 'explorer' | 'investor';
export const DEFAULT_TIER: AgeTier = 'explorer';

// Mascot/presentation knobs per tier — the single place to retune prominence.
export const tierConfig: Record<AgeTier, { pennyHeroSize: number }> = {
  explorer: { pennyHeroSize: 44 },
  investor: { pennyHeroSize: 32 },
};

/** The current child's live age tier (defaults to explorer until loaded). */
export function useAgeTier(): AgeTier {
  const { data } = useChildSession();
  return data?.age_tier ?? DEFAULT_TIER;
}
```

- [ ] **Step 3: Write the failing test** — create `src/lib/__tests__/tierCopy.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { buildHeroGreeting } from '../homeHero';
import { ENCOURAGEMENT } from '../tierCopy';

const base = { name: 'Sam', mode: 'start' as const, lessonLabel: 'Stocks 101', streakCount: 0, dueCount: 0 };

describe('tier-aware hero greeting', () => {
  it('explorer copy is warm and uses an emoji', () => {
    const g = buildHeroGreeting({ ...base, tier: 'explorer' });
    expect(g).toContain('Sam');
    expect(/\p{Emoji}/u.test(g)).toBe(true);
  });
  it('investor copy is cooler with no emoji', () => {
    const g = buildHeroGreeting({ ...base, tier: 'investor' });
    expect(g).toContain('Sam');
    expect(/\p{Extended_Pictographic}/u.test(g)).toBe(false);
  });
});

describe('tier encouragement lines', () => {
  it('provides a non-empty set for each tier', () => {
    expect(ENCOURAGEMENT.explorer.length).toBeGreaterThan(0);
    expect(ENCOURAGEMENT.investor.length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 4: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- tierCopy`
Expected: FAIL — `tierCopy` missing / `buildHeroGreeting` doesn't accept `tier`.

- [ ] **Step 5: Create `src/lib/tierCopy.ts`**

```ts
import type { AgeTier } from './ageTier';
import type { HeroGreetingCtx } from './homeHero';

/** Per-tier hero greeting builders. Explorer = warm + light emoji; investor = cool, no emoji. */
export const HERO_GREETING: Record<AgeTier, (ctx: HeroGreetingCtx) => string> = {
  explorer: (ctx) => {
    const name = ctx.name || 'there';
    if (ctx.dueCount > 0) {
      const plural = ctx.dueCount === 1 ? 'concept' : 'concepts';
      return `Welcome back, ${name}! You've got ${ctx.dueCount} ${plural} ready to review. 🧠`;
    }
    if (ctx.mode === 'caught_up') {
      return `Amazing work, ${name}! You've finished everything for now. 🎉 New lessons coming soon!`;
    }
    if (ctx.mode === 'continue') {
      const streak = ctx.streakCount > 1 ? ` ${ctx.streakCount}-day streak — keep it going!` : '';
      return `Welcome back, ${name}!${streak} Let's pick up ${ctx.lessonLabel ?? 'your next lesson'}.`;
    }
    return `Let's start your money journey, ${name}! First up: ${ctx.lessonLabel ?? 'your first lesson'} 📈`;
  },
  investor: (ctx) => {
    const name = ctx.name || 'there';
    if (ctx.dueCount > 0) {
      const plural = ctx.dueCount === 1 ? 'concept' : 'concepts';
      return `Welcome back, ${name}. You have ${ctx.dueCount} ${plural} to review.`;
    }
    if (ctx.mode === 'caught_up') {
      return `Nice work, ${name}. You're all caught up — more lessons coming soon.`;
    }
    if (ctx.mode === 'continue') {
      const streak = ctx.streakCount > 1 ? ` ${ctx.streakCount}-day streak.` : '';
      return `Welcome back, ${name}.${streak} Pick up where you left off: ${ctx.lessonLabel ?? 'your next lesson'}.`;
    }
    return `Let's get started, ${name}. First up: ${ctx.lessonLabel ?? 'your first lesson'}.`;
  },
};

/** Per-tier rotating encouragement lines for the lesson header. */
export const ENCOURAGEMENT: Record<AgeTier, string[]> = {
  explorer: [
    "You're doing great!",
    'Keep it up! 💪',
    'Nice thinking! 🌟',
    "You've got this!",
  ],
  investor: [
    'Solid progress.',
    'Keep going.',
    'Good reasoning.',
    'On track.',
  ],
};
```

- [ ] **Step 6: Make `buildHeroGreeting` tier-aware** — in `src/lib/homeHero.ts`, add `tier: AgeTier` to `HeroGreetingCtx` and delegate to the map. Replace the body of `buildHeroGreeting` with the delegation (keep the type export):

```ts
import { type AgeTier, DEFAULT_TIER } from './ageTier';
import { HERO_GREETING } from './tierCopy';

export type HeroMode = 'start' | 'continue' | 'caught_up';

export interface HeroGreetingCtx {
  name: string;
  mode: HeroMode;
  lessonLabel: string | null;
  streakCount: number;
  dueCount: number;
  tier?: AgeTier; // optional so existing callers compile; HomeHero passes it explicitly in Task 4
}

export function buildHeroGreeting(ctx: HeroGreetingCtx): string {
  return HERO_GREETING[ctx.tier ?? DEFAULT_TIER](ctx);
}
```
`tier` is **optional with a default** so this task commits green on its own (the existing HomeHero caller that omits `tier` still type-checks; Task 4 makes it pass the real tier). `HeroGreetingCtx` is imported type-only in `tierCopy.ts` while `homeHero.ts` value-imports `HERO_GREETING` — no runtime cycle.

- [ ] **Step 7: Run tests + typecheck**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- tierCopy && npx tsc -b`
Expected: tierCopy tests pass; tsc clean (the optional `tier` keeps existing callers valid).

- [ ] **Step 8: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/auth.ts invest-ed/frontend/src/lib/ageTier.ts invest-ed/frontend/src/lib/tierCopy.ts invest-ed/frontend/src/lib/homeHero.ts invest-ed/frontend/src/lib/__tests__/tierCopy.test.ts
git commit -m "feat(fe): age-tier foundations + tier-aware hero greeting copy

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Wire tier into HomeHero (greeting + Penny size) + LessonChrome encouragement

**Files:** Modify `src/components/child/HomeHero.tsx`, `src/components/child/lesson/LessonChrome.tsx`; Test `src/components/child/__tests__/HomeHero.test.tsx` (existing).

- [ ] **Step 1: Update HomeHero** — READ `src/components/child/HomeHero.tsx`. Add the imports:
```tsx
import { tierConfig, type AgeTier } from '@/lib/ageTier';
```
Derive the tier from the session and use it for the greeting + Penny size. The component already has `const { data: me } = useChildSession();`. Add:
```tsx
  const tier: AgeTier = me?.age_tier ?? 'explorer';
```
Pass `tier` into the templated greeting call (`buildHeroGreeting({ name, mode: next.mode, lessonLabel: next.lessonLabel, streakCount, dueCount, tier })`) and set the hero Penny size from config:
```tsx
        <Penny size={tierConfig[tier].pennyHeroSize} mood="happy" />
```
(Leave the AI greeting path as-is — the backend already injects the tier directive there.)

- [ ] **Step 2: Update LessonChrome encouragement** — READ `src/components/child/lesson/LessonChrome.tsx`. Remove the local `PENNY_LINES` const and source the lines from tier copy:
```tsx
import { useAgeTier } from '@/lib/ageTier';
import { ENCOURAGEMENT } from '@/lib/tierCopy';
```
Inside the component, replace the `PENNY_LINES` usage:
```tsx
  const lines = ENCOURAGEMENT[useAgeTier()];
  const line = lines[(position - 1) % lines.length];
```

- [ ] **Step 3: Update the HomeHero test** — in `src/components/child/__tests__/HomeHero.test.tsx`, the `useChildSession` mock returns `{ data: { username: 'Sam', is_premium: false } }`. Add `age_tier` and assert tier-driven rendering. Add a second describe/it that mocks an investor and checks the cooler greeting + smaller Penny. Concretely, change the mock to accept a tier and add a test:

```tsx
// existing mock — add age_tier
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: () => ({ data: { username: 'Sam', is_premium: false, age_tier: 'explorer' } }) }));
```
Then add an assertion in an existing or new test that the explorer greeting text renders (e.g. contains an emoji / the warm phrasing). If you need to test the investor variant in the same file, use `vi.doMock`/a separate test file with the investor mock; keep it simple — at minimum assert the explorer hero renders without a11y violations (the existing axe test) and that `buildHeroGreeting` tier wiring compiles. Do not weaken existing assertions.

- [ ] **Step 4: Run tests + typecheck + lint**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- HomeHero LessonChrome && npx tsc -b && npm run lint`
Expected: tests pass; tsc now clean (the Task 3 caller gap is closed); lint clean (known warnings only). Run the FULL `npm test` to catch the `tests/unit/` mirror (e.g. `child-LessonChrome`, `child-HomeHero`) — update any mock that now needs `age_tier` or that asserted the old `PENNY_LINES` copy (add `age_tier: 'explorer'` to `useChildSession` mocks; the explorer encouragement lines match the old copy, so most assertions hold).

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src invest-ed/frontend/tests
git commit -m "feat(fe): tier-aware HomeHero greeting + Penny size + lesson encouragement

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Tier-aware default module ordering

**Files:** Create `src/lib/tierModuleOrder.ts`; Modify `src/pages/child/Home.tsx`, `src/pages/child/Lessons.tsx`; Test `src/lib/__tests__/tierModuleOrder.test.ts` (new).

- [ ] **Step 1: Write the failing test** — create `src/lib/__tests__/tierModuleOrder.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { orderModulesForTier } from '../tierModuleOrder';

const mods = [
  { id: 'a', topic: 'budgeting', order_index: 0 },
  { id: 'b', topic: 'stocks', order_index: 1 },
  { id: 'c', topic: 'crypto', order_index: 2 },
  { id: 'd', topic: 'taxes', order_index: 3 },
];

describe('orderModulesForTier', () => {
  it('investor surfaces investing topics first', () => {
    const ids = orderModulesForTier(mods, 'investor').map((m) => m.id);
    expect(ids.indexOf('b')).toBeLessThan(ids.indexOf('a')); // stocks before budgeting
    expect(ids.indexOf('c')).toBeLessThan(ids.indexOf('a')); // crypto before budgeting
  });
  it('explorer surfaces foundations first', () => {
    const ids = orderModulesForTier(mods, 'explorer').map((m) => m.id);
    expect(ids.indexOf('a')).toBeLessThan(ids.indexOf('b')); // budgeting before stocks
  });
  it('falls back to order_index for unmapped/tied topics', () => {
    const ids = orderModulesForTier(mods, 'investor').map((m) => m.id);
    // taxes is unmapped for investor -> ordered after the prioritized ones, by order_index
    expect(ids[ids.length - 1]).toBe('d');
  });
  it('does not mutate the input array', () => {
    const copy = [...mods];
    orderModulesForTier(mods, 'investor');
    expect(mods).toEqual(copy);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- tierModuleOrder`
Expected: FAIL — module missing.

- [ ] **Step 3: Create `src/lib/tierModuleOrder.ts`**

```ts
import type { AgeTier } from './ageTier';

// topic -> sort priority (lower = earlier). Unmapped topics fall back to order_index.
// The ONE place to retune per-tier module surfacing.
const PRIORITY: Record<AgeTier, Record<string, number>> = {
  explorer: { budgeting: 0, savings: 1, debt: 2 },
  investor: { stocks: 0, crypto: 1, risk: 2, real_estate: 3 },
};

const FALLBACK = Number.MAX_SAFE_INTEGER;

/** Stable tier-aware ordering by (topic priority, then order_index). Never mutates input. */
export function orderModulesForTier<T extends { topic: string; order_index: number }>(
  modules: T[],
  tier: AgeTier,
): T[] {
  const prio = PRIORITY[tier];
  return [...modules].sort((a, b) => {
    const pa = prio[a.topic] ?? FALLBACK;
    const pb = prio[b.topic] ?? FALLBACK;
    if (pa !== pb) return pa - pb;
    return a.order_index - b.order_index;
  });
}
```

- [ ] **Step 4: Apply in `Home.tsx`** — READ `src/pages/child/Home.tsx`. It currently does `const modules = [...(modulesQ.data ?? [])].sort((a, b) => a.order_index - b.order_index);`. Add the imports and replace the sort:
```tsx
import { orderModulesForTier } from '@/lib/tierModuleOrder';
import { useAgeTier } from '@/lib/ageTier';
```
```tsx
  const tier = useAgeTier();
  const modules = orderModulesForTier(modulesQ.data ?? [], tier);
```

- [ ] **Step 5: Apply in `Lessons.tsx`** — READ `src/pages/child/Lessons.tsx`. It currently does `const modules = modulesQ.data ?? [];`. Order it by tier (the page already loads `me`, so derive the tier from `me?.age_tier ?? 'explorer'` to avoid an extra hook, OR use `useAgeTier()`):
```tsx
import { orderModulesForTier } from '@/lib/tierModuleOrder';
```
```tsx
  const tier = (me?.age_tier ?? 'explorer') as 'explorer' | 'investor';
  const modules = orderModulesForTier(modulesQ.data ?? [], tier);
```
(The downstream `lessonsByModuleId` loop and `lessonQueries` iterate `modules` in order — keep them after this reordering so the display follows the tier order.)

- [ ] **Step 6: Run tests + typecheck + lint + full suite**

Run: `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npm test -- tierModuleOrder && npx tsc -b && npm run lint && npm test`
Expected: tierModuleOrder tests pass; tsc + lint clean; FULL suite 0 failed. If a Home/Lessons test asserted a specific module order, update it for the tier-aware order (mock `useChildSession`/`useAgeTier` with a known tier; don't weaken).

- [ ] **Step 7: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src invest-ed/frontend/tests
git commit -m "feat(fe): tier-aware default module ordering on Home + Lessons

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Full regression, iOS sync, push

**Files:** none.

- [ ] **Step 1: Backend regression** — `cd "/Users/leeashmore/Local Repo/invest-ed/backend" && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Expected: all pass; ruff clean. (DB hang ~90s+ = environmental; rely on CI.)

- [ ] **Step 2: Frontend regression** — `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean (known warnings only); all suites pass; build OK.

- [ ] **Step 3: iOS sync** — `cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && npx cap sync ios`
Expected: "Sync finished". If `git status` shows tracked `invest-ed/frontend/ios` changes, commit them:
```bash
cd "/Users/leeashmore/Local Repo"
git add -A invest-ed/frontend/ios && git commit -m "chore(ios): cap sync after age-tier mode

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" || echo "nothing to commit from cap sync"
```

- [ ] **Step 4: Push** — `cd "/Users/leeashmore/Local Repo" && git push origin main`

- [ ] **Step 5: Report** — summarise commits; note Vercel/Railway deploy on green CI; the tier flips automatically as a child ages (no migration); iOS shows the web bundle so a USER Xcode rebuild surfaces it on device (copy/ordering/size only, no native change).

---

## Self-Review

**Spec coverage:**
- Tier derivation (`age_tier.py`, boundary 14, `AgeTier`) + `User.age_tier` property + `UserProfile.age_tier` exposure → Task 1. ✓
- Always-live (computed via `date.today()`, no column, no migration) → Task 1 (property) + plan-wide "no migration". ✓
- Tone/copy: LLM register directive (greeting + coach, server-trusted `current_user.age_tier`) → Task 2; templated hero copy + encouragement → Tasks 3–4. ✓
- Mascot prominence (`tierConfig` → HomeHero Penny size) → Tasks 3–4. ✓
- Module ordering (`tierModuleOrder` on Home + Lessons) → Task 5. ✓
- Configurability single-sources: `age_tier.py` (boundary + `AGE_REGISTER_DIRECTIVE`), `ageTier.ts` (`tierConfig`), `tierCopy.ts`, `tierModuleOrder.ts` (`PRIORITY`) — Tasks 1–5; tests reference constants. ✓
- Silent (no visible label), no override, Simulator deferred → honored (nothing renders a tier badge; no toggle; no Simulator change). ✓
- iOS sync close-out → Task 6. ✓

**Placeholder scan:** No TBD/TODO; code shown in every step. The "READ the file" notes (HomeHero/LessonChrome/Lessons) have explicit edit instructions + the exact lines to change, not placeholders. ✓

**Type consistency:** `AgeTier = 'explorer' | 'investor'` defined once (backend `age_tier.py`, FE `ageTier.ts`) and used identically; `age_tier(dob, today) -> AgeTier`; `AGE_REGISTER_DIRECTIVE[tier]` keyed by the same union; `HeroGreetingCtx.tier` added in Task 3 and supplied by HomeHero in Task 4; `buildHeroGreeting(ctx)` signature consistent; `orderModulesForTier(modules, tier)` defined in Task 5 and called identically in Home/Lessons; `tierConfig[tier].pennyHeroSize` consistent between Task 3 (def) and Task 4 (use). ✓
