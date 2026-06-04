# Region / Currency Preferences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give a child two independent, easy-to-change preferences — a **learning region** (`content_region`, US/GB/HK) that geares lessons + simulator focus, and a **practice currency** (`currency_code`) — without ever touching the legal `country_code` that drives the COPPA/UK-GDPR consent regime.

**Architecture:** Add a nullable `User.content_region` column (NULL ⇒ falls back to `country_code`). A pure helper `content_region_for(user)` returns the effective region; all *module-country* gating (`content.py`, `recommendation_service.py`, `analytics_service.py`) switches from `user.country_code` to this helper, while `compliance.py` / `consent_service.py` keep using `country_code` untouched. `PATCH /users/me` gains an optional, validated `content_region` field (currency already accepted). Two new independent React controls (`RegionSwitcher`, `CurrencySelector`) call the existing `updatePreferences` client and invalidate the right query keys. The simulator Market reorders its exchange groups so the chosen region's exchange leads.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres (backend); React 18 + Vite + TS + TanStack Query + Tailwind v4 + shadcn/ui + Vitest/vitest-axe (frontend).

---

## Reference facts (verified — read before starting)

- **Alembic single head = `a7b8c9d0e1f2`** (SP-D1 `parent_identity` migration). Verified by parsing every `alembic/versions/*.py`: it is the only `revision` never referenced as a `down_revision`. `alembic heads`/`alembic upgrade head` may **hang locally** (env import side-effect / Postgres) — that's environmental; rely on CI for migration verification. The new migration's `down_revision` MUST be `"a7b8c9d0e1f2"`.
- **`/users/me` response schema** is `UserProfile` in `app/schemas/user.py` (the router uses `response_model=UserProfile`). There is **no** separate `Me` schema in `app/schemas/auth.py` (that file's `RegisterRequest` is unrelated). So only `UserProfile` needs the new field on the backend; the frontend `Me` type lives in `src/api/auth.ts`.
- **PATCH request schema** is `UpdatePreferencesRequest` (app/schemas/user.py) — NOT `PreferencesUpdate`. The router applies each field with `if payload.X is not None`.
- **Existing helper** `is_module_accessible(user_country, is_premium_user, module_country_codes, module_is_premium)` lives in `app/services/content_service.py` and already does the country/premium check.
- **Module-country gating sites:**
  - `app/routers/content.py:50` and `:70` — `country_ok = not module.country_codes or current_user.country_code in module.country_codes`; plus the two `is_module_accessible(current_user.country_code, ...)` calls at `:53-55` and `:73-75`.
  - `app/services/recommendation_service.py:60` and `:404` — `if module.country_codes and user.country_code not in module.country_codes:` (var is `module` at 60, `m` at 404).
  - `app/services/analytics_service.py:41` — `Module.country_codes.any(country_code)`; the `country_code` param is passed by the caller `app/routers/parent.py:49` as `r.country_code`.
- **Do NOT touch** `app/services/compliance.py` or `app/services/consent_service.py` — they legitimately key on `country_code` for the consent regime.
- **All 12 seeded modules are `country_codes: []` (global)** → region gating is future-ready; the only *visible* effect today is the simulator exchange ordering.
- **Market** (`src/pages/child/Market.tsx`): groups quotes by `s.exchange`, sorted alphabetically via `groupByExchange` (line 30-36, sort `([a],[b]) => a.localeCompare(b)`). Group labels map NASDAQ/NYSE→US, LSE→UK, HKEX→Hong Kong (lines 23-28). It does **not** currently read `me`.
- **Quests header** (`src/pages/child/Lessons.tsx:41`): `<h1>Quests</h1>` then a subtitle `<p>`.
- **`ProfileMenu`** (`src/components/child/ProfileMenu.tsx`): child settings menu with a Profile editor dialog/bottom-sheet using `authApi.updatePreferences({ topic_path })` and `qc.invalidateQueries({ queryKey: ['me'] })`. Reads current via `qc.getQueryData<Me>(['me'])`.
- **`formatCurrency(value, code)`** + `getCurrencySymbol(code)` in `src/lib/currency.ts` (knows USD/GBP/HKD/EUR/JPY symbols).
- **Region → exchange** focus: `US → [NASDAQ, NYSE]`, `GB → [LSE]`, `HK → [HKEX]`.
- **Currency scope decision (YAGNI):** there is no stored "home currency" field — `currency_code` *is* the persisted choice (set at registration). `CurrencySelector` therefore offers `dedupe([currentCurrency, 'USD','GBP','HKD'])` so the registration currency stays selectable while it's the current value, plus the three majors. We do **not** add a separate home-currency column (scope creep, and country_code-adjacent).

## Commands

- Backend (from `invest-ed/backend`): test `/Users/leeashmore/Local Repo/.venv/bin/pytest`; lint `/Users/leeashmore/Local Repo/.venv/bin/ruff check .`; migrate `/Users/leeashmore/Local Repo/.venv/bin/alembic upgrade head` (may hang locally → rely on CI). Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + conftest `client`/`admin_client`/`db_session` fixtures — never a raw `AsyncClient`.
- Frontend (from `invest-ed/frontend`): `npx tsc -b`; `npm run lint` (one pre-existing `button.tsx` fast-refresh warning is expected); `npm test`; `npm run build`.
- Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end every commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend only on green CI (6 jobs incl. iOS Capacitor compile).

---

## Task 1: `content_region` column + migration + `content_region_for` helper

**Files:**
- Modify: `invest-ed/backend/app/models/user.py:23` (add column after `topic_path`)
- Modify: `invest-ed/backend/app/services/content_service.py` (add helper)
- Create: `invest-ed/backend/alembic/versions/b8c9d0e1f2a3_add_content_region_to_users.py`
- Test: `invest-ed/backend/tests/test_content_region_helper.py`

- [ ] **Step 1: Write the failing test for the helper**

Create `invest-ed/backend/tests/test_content_region_helper.py`:

```python
from types import SimpleNamespace

from app.services.content_service import content_region_for


def test_content_region_falls_back_to_country_code_when_unset():
    user = SimpleNamespace(country_code="US", content_region=None)
    assert content_region_for(user) == "US"


def test_content_region_used_when_set():
    user = SimpleNamespace(country_code="US", content_region="HK")
    assert content_region_for(user) == "HK"


def test_content_region_falls_back_when_attribute_missing():
    # Defensive: objects without the attribute still resolve to country_code.
    user = SimpleNamespace(country_code="GB")
    assert content_region_for(user) == "GB"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_content_region_helper.py -v`
Expected: FAIL with `ImportError: cannot import name 'content_region_for'`.

- [ ] **Step 3: Add the helper**

In `invest-ed/backend/app/services/content_service.py`, after `compute_level` (or near `is_module_accessible`), add:

```python
def content_region_for(user) -> str:
    """Effective *learning region* used for module-country gating.

    Returns the child's chosen ``content_region`` (US/GB/HK), falling back to
    their legal ``country_code`` when unset (NULL). Uses ``getattr`` so it works
    on any object exposing ``country_code`` and avoids importing the User model.

    NEVER mutate ``country_code`` from region features — it drives the
    COPPA/UK-GDPR consent regime (compliance.py / consent_service.py).
    """
    return getattr(user, "content_region", None) or user.country_code
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_content_region_helper.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Add the model column**

In `invest-ed/backend/app/models/user.py`, immediately after line 23 (`topic_path: Mapped[str | None] = ...`):

```python
    content_region: Mapped[str | None] = mapped_column(String(2), nullable=True)
```

(`String` is already imported in this file.)

- [ ] **Step 6: Write the migration**

Create `invest-ed/backend/alembic/versions/b8c9d0e1f2a3_add_content_region_to_users.py`:

```python
"""add content_region to users

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-04

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("content_region", sa.String(length=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "content_region")
```

- [ ] **Step 7: Verify the migration head chains cleanly (offline)**

Run: `cd invest-ed/backend && grep -rn "down_revision" alembic/versions/ | grep "b8c9d0e1f2a3" ; grep -rln "a7b8c9d0e1f2" alembic/versions/`
Expected: the new file sets `down_revision = "a7b8c9d0e1f2"`, and `a7b8c9d0e1f2` is now referenced as a down_revision exactly once (by the new file) — i.e. `b8c9d0e1f2a3` is the new single head. (Skip `alembic upgrade head` if it hangs — CI runs it.)

- [ ] **Step 8: Run ruff + the helper test**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_content_region_helper.py -v`
Expected: ruff clean; 3 passed.

- [ ] **Step 9: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/models/user.py invest-ed/backend/app/services/content_service.py invest-ed/backend/alembic/versions/b8c9d0e1f2a3_add_content_region_to_users.py invest-ed/backend/tests/test_content_region_helper.py
git commit -m "feat(region): add content_region column + content_region_for helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Wire region-gating to the effective region

**Files:**
- Modify: `invest-ed/backend/app/routers/content.py:50,53-55,70,73-75`
- Modify: `invest-ed/backend/app/services/recommendation_service.py:60,404`
- Modify: `invest-ed/backend/app/routers/parent.py:49`
- Test: `invest-ed/backend/tests/test_region_gating.py`

**Note:** `analytics_service.build_child_analytics` keeps its `country_code` param name (avoids breaking existing callers/tests); only the *caller* (`parent.py`) changes to pass the child's effective region.

- [ ] **Step 1: Write the failing integration test**

Create `invest-ed/backend/tests/test_region_gating.py`. This mirrors the existing content-router test style — read `tests/conftest.py` and an existing content test (e.g. `tests/test_content.py` if present) first to match fixture usage. Use the shared `client`/`db_session` fixtures and `pytestmark`.

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_module_list_uses_content_region_but_all_global_modules_show(client, db_session):
    """A US child with content_region='HK' still sees all global modules
    (seed data is all country_codes=[]), proving the effective-region path
    is wired without regressing global visibility."""
    # Register a US child, then PATCH content_region to HK.
    # (Follow the registration helper used by existing tests in this suite.)
    me = await _register_child(client, country_code="US", currency_code="USD")
    patch = await client.patch("/users/me", json={"content_region": "HK"})
    assert patch.status_code == 200
    assert patch.json()["content_region"] == "HK"

    resp = await client.get("/content/modules")
    assert resp.status_code == 200
    # All seeded modules are global → still visible regardless of region.
    assert len(resp.json()) >= 1
```

> Implementer: replace `_register_child` with this suite's actual registration/login flow (inspect a sibling test). The behavioural assertion that matters: switching `content_region` does not hide global modules and the request succeeds.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_region_gating.py -v`
Expected: FAIL — `content_region` not yet accepted by PATCH (Task 3) **or** the helper not yet wired. (If it errors on PATCH validation, that's fine — Task 3 adds it; you may temporarily set `content_region` directly via `db_session` to assert the gating path, then rely on the full flow after Task 3. Keep the test asserting the gating behaviour.)

- [ ] **Step 3: Wire `content.py`**

At top of `invest-ed/backend/app/routers/content.py`, ensure the import includes the helper (line ~24 currently imports `is_module_accessible`):

```python
from app.services.content_service import (
    content_region_for,
    is_module_accessible,
)
```

Replace line 50:
```python
    country_ok = not module.country_codes or content_region_for(current_user) in module.country_codes
```
Replace the `is_module_accessible` call at lines 53-55:
```python
    if not is_module_accessible(
        content_region_for(current_user), is_premium(current_user),
        module.country_codes, module.is_premium,
    ):
```
Replace line 70:
```python
        country_ok = not m.country_codes or content_region_for(current_user) in m.country_codes
```
Replace the `is_module_accessible` call at lines 73-75:
```python
        accessible = is_module_accessible(
            content_region_for(current_user), is_premium(current_user),
            m.country_codes, m.is_premium,
        )
```

- [ ] **Step 4: Wire `recommendation_service.py`**

Add the import near the top: `from app.services.content_service import content_region_for` (check it isn't already imported; if `content_service` is imported as a module, use `content_service.content_region_for`).

Replace line 60:
```python
    if module.country_codes and content_region_for(user) not in module.country_codes:
```
Replace line 404:
```python
        if m.country_codes and content_region_for(user) not in m.country_codes:
```

- [ ] **Step 5: Wire the analytics caller in `parent.py`**

Add `from app.services.content_service import content_region_for` to `app/routers/parent.py` imports (if not present). Replace line 49:
```python
            analytics = await build_child_analytics(session, r.id, content_region_for(r))
```
(Leave `analytics_service.build_child_analytics` and its `country_code` param unchanged.)

- [ ] **Step 6: Run the region-gating test + full backend suite**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_region_gating.py -v` then `/Users/leeashmore/Local\ Repo/.venv/bin/pytest`
Expected: new test passes; no regressions. (If the local Postgres hangs ~90s+, that's environmental — rely on CI.)

- [ ] **Step 7: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/routers/content.py invest-ed/backend/app/services/recommendation_service.py invest-ed/backend/app/routers/parent.py invest-ed/backend/tests/test_region_gating.py
git commit -m "feat(region): gate module content on effective content_region

Routes content/recommendation/analytics module-country matching through
content_region_for(); consent/compliance keep country_code untouched.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: PATCH/schema support + expose `content_region` on the profile

**Files:**
- Modify: `invest-ed/backend/app/schemas/user.py` (`UserProfile` + `UpdatePreferencesRequest`)
- Modify: `invest-ed/backend/app/routers/users.py:51-56`
- Test: `invest-ed/backend/tests/test_update_content_region.py`

- [ ] **Step 1: Write the failing endpoint test**

Create `invest-ed/backend/tests/test_update_content_region.py` (match the existing PATCH test style — inspect any test that already PATCHes `/users/me`):

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_patch_accepts_valid_content_region(client):
    await _register_child(client, country_code="US", currency_code="USD")
    resp = await client.patch("/users/me", json={"content_region": "GB"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["content_region"] == "GB"
    assert body["country_code"] == "US"  # legal country untouched


async def test_patch_rejects_unsupported_region(client):
    await _register_child(client, country_code="US", currency_code="USD")
    resp = await client.patch("/users/me", json={"content_region": "FR"})
    assert resp.status_code == 422


async def test_patch_currency_still_works_independently(client):
    await _register_child(client, country_code="US", currency_code="USD")
    resp = await client.patch("/users/me", json={"currency_code": "HKD"})
    assert resp.status_code == 200
    assert resp.json()["currency_code"] == "HKD"
    # content_region not set by a currency change
    assert resp.json()["content_region"] is None
```

> Implementer: replace `_register_child` with the suite's real helper.

- [ ] **Step 2: Run to verify failure**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_update_content_region.py -v`
Expected: FAIL — `content_region` not in response / not accepted (422 on the valid case or KeyError).

- [ ] **Step 3: Add `content_region` to `UserProfile`**

In `invest-ed/backend/app/schemas/user.py`, add to `UserProfile` after `topic_path` (line 20):

```python
    content_region: str | None = None
```

- [ ] **Step 4: Add a validated `content_region` to `UpdatePreferencesRequest`**

In the same file, add to `UpdatePreferencesRequest` (after `topic_path`, line 33):

```python
    content_region: str | None = None
```

Add module-level constant near the other regexes (line ~10):
```python
_SUPPORTED_REGIONS = {"US", "GB", "HK"}
```

Add validators (mirror the country_code style) inside `UpdatePreferencesRequest`:
```python
    @field_validator("content_region", mode="before")
    @classmethod
    def uppercase_region(cls, v):
        if isinstance(v, str):
            return v.upper().strip()
        return v

    @field_validator("content_region")
    @classmethod
    def validate_region(cls, v):
        if v is None:
            return v
        if v not in _SUPPORTED_REGIONS:
            raise ValueError("content_region must be one of US, GB, HK")
        return v
```

- [ ] **Step 5: Apply `content_region` in the router**

In `invest-ed/backend/app/routers/users.py`, inside `update_preferences` after the `topic_path` block (line 55-56), add:

```python
    if payload.content_region is not None:
        current_user.content_region = payload.content_region
```

- [ ] **Step 6: Run the endpoint test + full suite**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_update_content_region.py -v` then `/Users/leeashmore/Local\ Repo/.venv/bin/pytest`
Expected: 3 passed; no regressions.

- [ ] **Step 7: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/user.py invest-ed/backend/app/routers/users.py invest-ed/backend/tests/test_update_content_region.py
git commit -m "feat(region): accept + expose content_region on /users/me (US/GB/HK)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Frontend `RegionSwitcher` + `CurrencySelector` + types + API

**Files:**
- Modify: `invest-ed/frontend/src/api/auth.ts` (`Me` type + `updatePreferences` payload type)
- Create: `invest-ed/frontend/src/lib/region.ts` (region + currency constants)
- Create: `invest-ed/frontend/src/components/child/RegionSwitcher.tsx`
- Create: `invest-ed/frontend/src/components/child/CurrencySelector.tsx`
- Test: `invest-ed/frontend/src/components/child/RegionSwitcher.test.tsx`
- Test: `invest-ed/frontend/src/components/child/CurrencySelector.test.tsx`

- [ ] **Step 1: Extend the `Me` type + `updatePreferences` payload**

In `invest-ed/frontend/src/api/auth.ts`:
- Add to the `Me` type (after `topic_path`, line 14): `content_region: string | null;`
- Replace the `updatePreferences` signature (line 40) so all three prefs are optional:

```typescript
  updatePreferences: (body: {
    topic_path?: string | null;
    content_region?: string | null;
    currency_code?: string | null;
  }) =>
    apiFetch<Me>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
```

- [ ] **Step 2: Create the region/currency constants**

Create `invest-ed/frontend/src/lib/region.ts`:

```typescript
export type RegionCode = 'US' | 'GB' | 'HK';

export const REGIONS: { code: RegionCode; flag: string; label: string }[] = [
  { code: 'US', flag: '🇺🇸', label: 'US' },
  { code: 'GB', flag: '🇬🇧', label: 'UK' },
  { code: 'HK', flag: '🇭🇰', label: 'HK' },
];

// Exchanges featured first in the simulator for each region.
export const REGION_EXCHANGES: Record<RegionCode, string[]> = {
  US: ['NASDAQ', 'NYSE'],
  GB: ['LSE'],
  HK: ['HKEX'],
};

export const MAJOR_CURRENCIES = ['USD', 'GBP', 'HKD'] as const;

/** Practice-currency options: the child's current currency plus the majors, deduped. */
export function currencyOptions(currentCurrency: string): string[] {
  return Array.from(new Set([currentCurrency, ...MAJOR_CURRENCIES]));
}
```

- [ ] **Step 3: Write the failing `RegionSwitcher` test**

Create `invest-ed/frontend/src/components/child/RegionSwitcher.test.tsx`. Match the existing test setup (QueryClientProvider wrapper, `vitest-axe`) used by sibling component tests — read one (e.g. an existing `*.test.tsx` in `src/components/child/`) first.

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RegionSwitcher } from './RegionSwitcher';
import { authApi } from '@/api/auth';

vi.mock('@/api/auth', async (orig) => {
  const actual = await orig<typeof import('@/api/auth')>();
  return { ...actual, authApi: { ...actual.authApi, updatePreferences: vi.fn().mockResolvedValue({}) } };
});

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('RegionSwitcher', () => {
  it('renders three options with the current one marked', () => {
    wrap(<RegionSwitcher currentRegion="GB" />);
    const group = screen.getByRole('group', { name: /learning region/i });
    expect(within(group).getByRole('button', { name: /US/ })).toBeInTheDocument();
    expect(within(group).getByRole('button', { name: /UK/ })).toHaveAttribute('aria-current', 'true');
    expect(within(group).getByRole('button', { name: /HK/ })).toBeInTheDocument();
  });

  it('calls updatePreferences with content_region on change', async () => {
    wrap(<RegionSwitcher currentRegion="US" />);
    await userEvent.click(screen.getByRole('button', { name: /HK/ }));
    expect(authApi.updatePreferences).toHaveBeenCalledWith({ content_region: 'HK' });
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<RegionSwitcher currentRegion="US" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 4: Run to verify failure**

Run: `cd invest-ed/frontend && npm test -- RegionSwitcher`
Expected: FAIL — module `./RegionSwitcher` not found.

- [ ] **Step 5: Implement `RegionSwitcher`**

Create `invest-ed/frontend/src/components/child/RegionSwitcher.tsx`:

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/api/auth';
import { REGIONS, type RegionCode } from '@/lib/region';

export function RegionSwitcher({ currentRegion }: { currentRegion: RegionCode }) {
  const qc = useQueryClient();

  const save = useMutation({
    mutationFn: (content_region: RegionCode) => authApi.updatePreferences({ content_region }),
    onSuccess: () => {
      // Lessons + recommendations re-filter (future-ready) and market re-features the exchange.
      for (const key of [
        ['me'], ['modules'], ['recommendations'], ['module-levels'], ['level-lessons'],
        ['market-featured'], ['market-search'], ['portfolio'], ['portfolio-history'],
      ]) {
        qc.invalidateQueries({ queryKey: key });
      }
    },
  });

  return (
    <div
      role="group"
      aria-label="Learning region"
      className="inline-flex rounded-xl border border-brand-100 bg-card p-1"
    >
      {REGIONS.map((r) => {
        const active = r.code === currentRegion;
        return (
          <button
            key={r.code}
            type="button"
            aria-current={active ? 'true' : undefined}
            disabled={save.isPending}
            onClick={() => { if (!active) save.mutate(r.code); }}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-base font-semibold transition-colors min-h-[44px] ${
              active ? 'bg-brand-gradient text-white' : 'text-brand-700 hover:bg-brand-50'
            }`}
          >
            <span aria-hidden="true">{r.flag}</span>
            <span>{r.label}</span>
          </button>
        );
      })}
    </div>
  );
}
```

(Text labels are real; flags are `aria-hidden`. `text-base` keeps iOS ≥16px; `min-h-[44px]` keeps the touch target. `aria-current` marks the active option.)

- [ ] **Step 6: Run the RegionSwitcher test to verify pass**

Run: `cd invest-ed/frontend && npm test -- RegionSwitcher`
Expected: 3 passed.

- [ ] **Step 7: Write the failing `CurrencySelector` test**

Create `invest-ed/frontend/src/components/child/CurrencySelector.test.tsx` (same wrapper/mocks as Step 3):

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CurrencySelector } from './CurrencySelector';
import { authApi } from '@/api/auth';

vi.mock('@/api/auth', async (orig) => {
  const actual = await orig<typeof import('@/api/auth')>();
  return { ...actual, authApi: { ...actual.authApi, updatePreferences: vi.fn().mockResolvedValue({}) } };
});

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('CurrencySelector', () => {
  it('lists current + major currencies deduped', () => {
    wrap(<CurrencySelector currentCurrency="USD" />);
    const select = screen.getByLabelText(/practice currency/i) as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(['USD', 'GBP', 'HKD']); // USD deduped
  });

  it('keeps a non-major current currency in the list', () => {
    wrap(<CurrencySelector currentCurrency="EUR" />);
    const select = screen.getByLabelText(/practice currency/i) as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toEqual(['EUR', 'USD', 'GBP', 'HKD']);
  });

  it('calls updatePreferences with currency_code on change', async () => {
    wrap(<CurrencySelector currentCurrency="USD" />);
    await userEvent.selectOptions(screen.getByLabelText(/practice currency/i), 'HKD');
    expect(authApi.updatePreferences).toHaveBeenCalledWith({ currency_code: 'HKD' });
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<CurrencySelector currentCurrency="USD" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 8: Run to verify failure**

Run: `cd invest-ed/frontend && npm test -- CurrencySelector`
Expected: FAIL — module not found.

- [ ] **Step 9: Implement `CurrencySelector`**

Create `invest-ed/frontend/src/components/child/CurrencySelector.tsx`:

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/api/auth';
import { currencyOptions } from '@/lib/region';
import { getCurrencySymbol } from '@/lib/currency';

export function CurrencySelector({ currentCurrency }: { currentCurrency: string }) {
  const qc = useQueryClient();
  const options = currencyOptions(currentCurrency);

  const save = useMutation({
    mutationFn: (currency_code: string) => authApi.updatePreferences({ currency_code }),
    onSuccess: () => {
      // Independent of region: holdings persist, totals re-display converted.
      for (const key of [['me'], ['portfolio'], ['portfolio-history']]) {
        qc.invalidateQueries({ queryKey: key });
      }
    },
  });

  return (
    <div className="space-y-1.5">
      <label htmlFor="practice-currency" className="text-sm font-medium">
        Practice currency
      </label>
      <select
        id="practice-currency"
        aria-label="Practice currency"
        className="h-11 w-full rounded-md border border-input bg-background px-3 text-base"
        value={currentCurrency}
        disabled={save.isPending}
        onChange={(e) => save.mutate(e.target.value)}
      >
        {options.map((c) => (
          <option key={c} value={c}>
            {getCurrencySymbol(c)} {c}
          </option>
        ))}
      </select>
    </div>
  );
}
```

(`text-base` + `h-11` keep iOS ≥16px and a comfortable target; the `<label htmlFor>` + `aria-label` give it an accessible name.)

- [ ] **Step 10: Run both component tests + tsc**

Run: `cd invest-ed/frontend && npm test -- RegionSwitcher CurrencySelector && npx tsc -b`
Expected: all pass; tsc clean.

- [ ] **Step 11: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/auth.ts invest-ed/frontend/src/lib/region.ts invest-ed/frontend/src/components/child/RegionSwitcher.tsx invest-ed/frontend/src/components/child/CurrencySelector.tsx invest-ed/frontend/src/components/child/RegionSwitcher.test.tsx invest-ed/frontend/src/components/child/CurrencySelector.test.tsx
git commit -m "feat(region): RegionSwitcher + CurrencySelector controls + Me type/api

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Mount both controls in `ProfileMenu` + RegionSwitcher on Quests header

**Files:**
- Modify: `invest-ed/frontend/src/components/child/ProfileMenu.tsx`
- Modify: `invest-ed/frontend/src/pages/child/Lessons.tsx`

- [ ] **Step 1: Add a "Preferences" section to the ProfileMenu editor**

In `invest-ed/frontend/src/components/child/ProfileMenu.tsx`:
- Import the controls + region helper at the top:
```tsx
import { RegionSwitcher } from '@/components/child/RegionSwitcher';
import { CurrencySelector } from '@/components/child/CurrencySelector';
import type { RegionCode } from '@/lib/region';
```
- Inside `openEditor`/render, read the current values from the `me` query (already used via `qc.getQueryData<Me>(['me'])`). Add a derived `me` read in the component body:
```tsx
  const me = qc.getQueryData<Me>(['me']);
  const currentRegion = (me?.content_region ?? me?.country_code ?? 'US') as RegionCode;
  const currentCurrency = me?.currency_code ?? 'USD';
```
- In `editorContent`, after the existing "Interest area" block (before/after the Save button), add a Preferences section:
```tsx
      <div className="space-y-3 border-t border-line pt-4">
        <p className="text-sm font-semibold text-muted-foreground">Preferences</p>
        <div className="space-y-1.5">
          <span id="region-label" className="text-sm font-medium">Learning region</span>
          <div aria-labelledby="region-label">
            <RegionSwitcher currentRegion={currentRegion} />
          </div>
        </div>
        <CurrencySelector currentCurrency={currentCurrency} />
      </div>
```

> Note: `currentRegion` falls back through `content_region ?? country_code`. The `RegionSwitcher` already has its own `role="group"` label, so the wrapping `aria-labelledby` is supplementary — if the spec reviewer flags a double-label, drop the extra `<span>` and keep only the control's built-in label.

- [ ] **Step 2: Verify the ProfileMenu still renders (typecheck + existing tests)**

Run: `cd invest-ed/frontend && npx tsc -b && npm test -- ProfileMenu`
Expected: tsc clean; existing ProfileMenu tests (if any) pass. If there are none, this step is just tsc.

- [ ] **Step 3: Add the compact RegionSwitcher to the Quests header**

In `invest-ed/frontend/src/pages/child/Lessons.tsx`:
- Add imports:
```tsx
import { RegionSwitcher } from '@/components/child/RegionSwitcher';
import { authApi, type Me } from '@/api/auth';
import type { RegionCode } from '@/lib/region';
```
- Read `me` (it's cached app-wide; use a query so the header reacts to changes):
```tsx
  const { data: me } = useQuery<Me>({ queryKey: ['me'], queryFn: () => authApi.me(), staleTime: 60_000 });
  const currentRegion = (me?.content_region ?? me?.country_code ?? 'US') as RegionCode;
```
- Replace the `<h1>Quests</h1>` line with a header row that keeps the title and right-aligns the switcher:
```tsx
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-extrabold text-gray-900">Quests</h1>
        <RegionSwitcher currentRegion={currentRegion} />
      </div>
```

- [ ] **Step 4: Typecheck + lint**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint`
Expected: tsc clean; lint clean apart from the known pre-existing `button.tsx` fast-refresh warning.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/ProfileMenu.tsx invest-ed/frontend/src/pages/child/Lessons.tsx
git commit -m "feat(region): mount Region/Currency prefs in ProfileMenu + Quests header

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Simulator Market features the selected region's exchange first

**Files:**
- Modify: `invest-ed/frontend/src/pages/child/Market.tsx`
- Test: `invest-ed/frontend/src/pages/child/Market.region.test.tsx`

- [ ] **Step 1: Write the failing test for exchange ordering**

Create `invest-ed/frontend/src/pages/child/Market.region.test.tsx`. The cleanest, least-brittle target is the pure ordering helper, so first refactor `groupByExchange` to accept priority exchanges (Step 3) — but write the test first against the intended signature:

```tsx
import { describe, it, expect } from 'vitest';
import { groupByExchange } from './Market';

const quote = (exchange: string, ticker: string) =>
  ({ exchange, ticker, name: ticker, price: '1', currency: 'USD', change: 0, change_pct: 0 } as never);

describe('groupByExchange region prioritisation', () => {
  it('puts the region exchanges first, then the rest alphabetically', () => {
    const stocks = [quote('NASDAQ', 'AAPL'), quote('LSE', 'VOD'), quote('HKEX', '0700')];
    const order = groupByExchange(stocks, ['HKEX']).map(([ex]) => ex);
    expect(order[0]).toBe('HKEX');
    expect(order.slice(1)).toEqual(['LSE', 'NASDAQ']);
  });

  it('falls back to alphabetical when no priority given', () => {
    const stocks = [quote('NASDAQ', 'AAPL'), quote('LSE', 'VOD')];
    const order = groupByExchange(stocks, []).map(([ex]) => ex);
    expect(order).toEqual(['LSE', 'NASDAQ']);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd invest-ed/frontend && npm test -- Market.region`
Expected: FAIL — `groupByExchange` not exported / wrong arity.

- [ ] **Step 3: Refactor `groupByExchange` + read region in Market**

In `invest-ed/frontend/src/pages/child/Market.tsx`:
- Add imports:
```tsx
import { authApi, type Me } from '@/api/auth';
import { REGION_EXCHANGES, type RegionCode } from '@/lib/region';
```
- Export and extend `groupByExchange` (replace lines 30-36):
```tsx
export function groupByExchange(stocks: QuoteOut[], priority: string[] = []) {
  const groups: Record<string, QuoteOut[]> = {};
  for (const s of stocks) {
    (groups[s.exchange] ??= []).push(s);
  }
  const rank = (ex: string) => {
    const i = priority.indexOf(ex);
    return i === -1 ? priority.length : i;
  };
  return Object.entries(groups).sort(([a], [b]) => rank(a) - rank(b) || a.localeCompare(b));
}
```
- In the `Market` component, read the region from `me` and compute priority exchanges:
```tsx
  const { data: me } = useQuery<Me>({ queryKey: ['me'], queryFn: () => authApi.me(), staleTime: 60_000 });
  const region = (me?.content_region ?? me?.country_code ?? 'US') as RegionCode;
  const priorityExchanges = REGION_EXCHANGES[region] ?? [];
```
- Replace `const groups = groupByExchange(stocks);` (line 92) with:
```tsx
  const groups = groupByExchange(stocks, priorityExchanges);
```

- [ ] **Step 4: Run the test + tsc**

Run: `cd invest-ed/frontend && npm test -- Market.region && npx tsc -b`
Expected: 2 passed; tsc clean.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/child/Market.tsx invest-ed/frontend/src/pages/child/Market.region.test.tsx
git commit -m "feat(region): simulator Market features the chosen region's exchange first

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Full regression + push

**Files:** none (verification only)

- [ ] **Step 1: Backend regression**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest`
Expected: ruff clean; tests pass (pre-existing-failure baseline only). If the DB hangs ~90s+, note it and rely on CI.

- [ ] **Step 2: Frontend regression**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean except the known `button.tsx` warning; all tests pass; build succeeds.

- [ ] **Step 3: Confirm `country_code` was never written by the feature**

Run: `cd "/Users/leeashmore/Local Repo" && git diff main~6 -- invest-ed/backend | grep -nE "country_code\s*=" || echo "no country_code assignments added"`
Expected: no new `current_user.country_code = ...` / `user.country_code = ...` assignments (only `content_region` is written). Confirms the consent regime is untouched.

- [ ] **Step 4: Push**

```bash
cd "/Users/leeashmore/Local Repo"
git push origin main
```

- [ ] **Step 5: Watch CI**

Confirm all 6 CI jobs go green (frontend, backend, security, a11y, responsive, iOS Capacitor). Railway deploys the backend only on green CI; Vercel auto-deploys the frontend.

- [ ] **Step 6: Update PROGRESS + memory**

Mark the Country switcher row ✅ shipped in `invest-ed/docs/superpowers/PROGRESS.md` and note SP-E (parent/admin polish) is next; update `invest-ed/AGENTS.md` "Resume here" pointer accordingly.

---

## Self-review notes

- **Spec coverage:** two independent settings (content_region + currency_code) ✓ (T3/T4); helper with NULL fallback ✓ (T1); gating wired without touching consent ✓ (T2, verified T7-S3); PATCH validation US/GB/HK ✓ (T3); FE controls + a11y + iOS sizing ✓ (T4); ProfileMenu Preferences + Quests/Market headers ✓ (T5); Market exchange ordering ✓ (T6); query invalidation ✓ (T4 mutations). Region-specific lesson *content authoring* is explicitly out of scope (spec).
- **Corrections vs the spec's assumptions:** response schema is `UserProfile` (no `Me` schema in auth.py); request schema is `UpdatePreferencesRequest` (not `PreferencesUpdate`); there is no stored "home currency" field — `CurrencySelector` uses `dedupe([currentCurrency, USD, GBP, HKD])` (documented YAGNI choice).
- **Type consistency:** `RegionCode` ('US'|'GB'|'HK'), `REGION_EXCHANGES`, `currencyOptions`, `groupByExchange(stocks, priority)` are used consistently across T4/T5/T6.
- **Migration:** `down_revision = "a7b8c9d0e1f2"` (verified single head); new head `b8c9d0e1f2a3`.
