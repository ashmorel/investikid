# i18n Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put every static UI string behind an i18n system with a per-user, server-backed language preference and a Settings switcher, so a new catalog file translates the whole app with zero code changes (English-only at launch).

**Architecture:** A shared supported-languages registry (mirrored front/back). Backend gains an additive `User.language` column + a dedicated validated `PATCH /users/me/language`. Frontend adds `react-i18next` with lazy catalogs, a `useLanguage` hook (server = source of truth, localStorage cache, device-locale first-run default), and a reusable `LanguageSwitcher` placed in child + parent settings. Completeness of extraction is enforced by an ESLint `no-literal-string` guard plus a pseudo-locale.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic (backend); React 18 + Vite 7 + TypeScript + TanStack Query + `i18next`/`react-i18next` + `@capacitor/device` (frontend); pytest, vitest, vitest-axe, ESLint flat config.

**Spec:** `docs/superpowers/specs/2026-06-17-i18n-foundation-design.md`

**Branch:** `testing` (promote testing → staging → main on green CI). The migration is additive; **before applying in prod, ask whether to snapshot the DB first** (standing rule).

---

## File Structure

**Backend**
- Create `backend/app/core/languages.py` — supported-language registry + `is_supported_language()`.
- Create `backend/alembic/versions/<rev>_user_language.py` — additive `users.language` column.
- Modify `backend/app/models/user.py` — add `language` column.
- Modify `backend/app/schemas/user.py` — add `language` to `UserProfile`; add `UpdateLanguageRequest`.
- Modify `backend/app/routers/users.py` — add `PATCH /me/language`.
- Create `backend/tests/test_user_language.py` — endpoint + default + validation tests.
- Create `backend/tests/test_languages_registry.py` — parity contract test (shared with frontend list).

**Frontend**
- Create `frontend/src/i18n/languages.ts` — registry mirror (codes/endonyms/available).
- Create `frontend/src/i18n/index.ts` — i18next init (lazy catalogs, fallback en).
- Create `frontend/src/i18n/resolveLanguage.ts` — boot resolution (server ?? localStorage ?? device ?? en).
- Create `frontend/src/locales/en/*.json` — extracted English catalogs (namespaced).
- Create `frontend/src/hooks/useLanguage.ts` — read/change language; persists to backend + localStorage + i18n.
- Create `frontend/src/components/settings/LanguageSwitcher.tsx` — reusable control (mirrors `RegionSwitcher`).
- Modify `frontend/src/main.tsx` — init i18n before render.
- Modify `frontend/src/api/auth.ts` — `Me.language`; `authApi.updateLanguage()`.
- Modify `frontend/src/components/child/ProfileMenu.tsx` — mount `LanguageSwitcher`.
- Modify `frontend/src/pages/ParentDashboard.tsx` — mount `LanguageSwitcher`.
- Modify `frontend/package.json` — add deps.
- Modify `frontend/eslint.config.js` — add `no-literal-string` guard.
- Create `frontend/scripts/gen-pseudo-locale.mjs` — build `en-XA` from `en`.
- Create tests under `frontend/tests/unit/` and `frontend/src/**/__tests__/`.

---

## PHASE 1 — Infrastructure

### Task 1: Shared supported-languages registry

**Files:**
- Create: `backend/app/core/languages.py`
- Create: `frontend/src/i18n/languages.ts`
- Test: `backend/tests/test_languages_registry.py`

- [ ] **Step 1: Write the failing backend test**

Create `backend/tests/test_languages_registry.py`:

```python
import json
from pathlib import Path

from app.core.languages import SUPPORTED_LANGUAGES, is_supported_language


def test_supported_set_and_validator():
    codes = {lang["code"] for lang in SUPPORTED_LANGUAGES}
    assert codes == {"en", "es", "fr", "de", "zh-Hant", "zh-Hans"}
    assert is_supported_language("en") is True
    assert is_supported_language("zh-Hant") is True
    assert is_supported_language("xx") is False


def test_only_english_available_at_launch():
    available = {lang["code"] for lang in SUPPORTED_LANGUAGES if lang["available"]}
    assert available == {"en"}


def test_frontend_registry_codes_match_backend():
    # The frontend TS registry must list the exact same codes, or language
    # validation will diverge from what the switcher offers.
    ts = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n" / "languages.ts"
    text = ts.read_text(encoding="utf-8")
    backend_codes = sorted(lang["code"] for lang in SUPPORTED_LANGUAGES)
    for code in backend_codes:
        assert f"'{code}'" in text, f"frontend registry missing {code}"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_languages_registry.py -q`
Expected: FAIL (`ModuleNotFoundError: app.core.languages`).

- [ ] **Step 3: Implement the backend registry**

Create `backend/app/core/languages.py`:

```python
"""Single source of truth for app display languages (BCP-47).

`available` flips to True once a UI catalog ships for that language. Keep this
list in lockstep with frontend/src/i18n/languages.ts (a test enforces parity).
"""
from __future__ import annotations

SUPPORTED_LANGUAGES: list[dict] = [
    {"code": "en", "endonym": "English", "available": True},
    {"code": "es", "endonym": "Español", "available": False},
    {"code": "fr", "endonym": "Français", "available": False},
    {"code": "de", "endonym": "Deutsch", "available": False},
    {"code": "zh-Hant", "endonym": "繁體中文", "available": False},
    {"code": "zh-Hans", "endonym": "简体中文", "available": False},
]

_CODES = frozenset(lang["code"] for lang in SUPPORTED_LANGUAGES)


def is_supported_language(code: str) -> bool:
    return code in _CODES
```

- [ ] **Step 4: Implement the frontend registry**

Create `frontend/src/i18n/languages.ts`:

```typescript
// Single source of truth for display languages (BCP-47). Keep in lockstep with
// backend/app/core/languages.py — a backend test enforces code parity.
export type SupportedLanguage = {
  code: 'en' | 'es' | 'fr' | 'de' | 'zh-Hant' | 'zh-Hans';
  endonym: string;
  available: boolean; // true once a UI catalog ships
};

export const SUPPORTED_LANGUAGES: SupportedLanguage[] = [
  { code: 'en', endonym: 'English', available: true },
  { code: 'es', endonym: 'Español', available: false },
  { code: 'fr', endonym: 'Français', available: false },
  { code: 'de', endonym: 'Deutsch', available: false },
  { code: 'zh-Hant', endonym: '繁體中文', available: false },
  { code: 'zh-Hans', endonym: '简体中文', available: false },
];

export const AVAILABLE_LANGUAGES = SUPPORTED_LANGUAGES.filter((l) => l.available);
export const SUPPORTED_CODES = SUPPORTED_LANGUAGES.map((l) => l.code);
export type LanguageCode = SupportedLanguage['code'];

export function isSupportedLanguage(code: string): code is LanguageCode {
  return (SUPPORTED_CODES as string[]).includes(code);
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_languages_registry.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/languages.py frontend/src/i18n/languages.ts backend/tests/test_languages_registry.py
git commit -m "feat(i18n): shared supported-languages registry (front+back parity)"
```

---

### Task 2: Backend — user language preference (column, migration, schema, endpoint)

**Files:**
- Modify: `backend/app/models/user.py` (after `currency_code`, line ~23)
- Create: `backend/alembic/versions/<rev>_user_language.py`
- Modify: `backend/app/schemas/user.py` (UserProfile ~line 21; add UpdateLanguageRequest ~line 37)
- Modify: `backend/app/routers/users.py` (after `update_preferences`, ~line 82)
- Test: `backend/tests/test_user_language.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_user_language.py`:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_new_user_defaults_to_english(client, db_session):
    # The /me profile exposes a language; default is English.
    me = (await client.get("/users/me")).json()
    assert me["language"] == "en"


async def test_patch_language_persists(client):
    r = await client.patch("/users/me/language", json={"language": "zh-Hant"})
    assert r.status_code == 200
    assert r.json()["language"] == "zh-Hant"
    assert (await client.get("/users/me")).json()["language"] == "zh-Hant"


async def test_patch_rejects_unknown_language(client):
    r = await client.patch("/users/me/language", json={"language": "xx"})
    assert r.status_code == 422
    # unchanged
    assert (await client.get("/users/me")).json()["language"] == "en"
```

> Note: use the existing authenticated `client` fixture (same one used by other `/users/me` tests). If that fixture's user is shared across tests, split the persist/reject assertions so ordering can't mask the default — keep `test_new_user_defaults_to_english` independent of the PATCH tests by using a fresh client/user fixture if available (`admin_client` is a separate user).

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_user_language.py -q`
Expected: FAIL (`KeyError: 'language'` / 404 on the new route).

- [ ] **Step 3: Add the model column**

In `backend/app/models/user.py`, add after the `currency_code` line:

```python
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en")
```

- [ ] **Step 4: Write the migration**

First check the current head:

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: a single head `f3a4b5c6d7e8` (revise XP cap). Use it as `down_revision`.

Create `backend/alembic/versions/a1b2c3d4e5f6_user_language.py`:

```python
"""user display language preference (i18n foundation)

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-06-17 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Per-user UI display language (BCP-47). Additive; existing rows backfill to
    # English via server_default so the change is behaviorally inert.
    op.add_column(
        "users",
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
    )


def downgrade() -> None:
    op.drop_column("users", "language")
```

> If `alembic heads` shows a different/extra head, set `down_revision` to the real current head and re-run `alembic heads` after creating the file to confirm a single head.

- [ ] **Step 5: Apply the migration locally**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head`
Expected: `Running upgrade f3a4b5c6d7e8 -> a1b2c3d4e5f6`.

- [ ] **Step 6: Add the schema field + request model**

In `backend/app/schemas/user.py`, add to `UserProfile` (after `currency_code`):

```python
    language: str = "en"
```

And add a new request model (near `UpdatePreferencesRequest`):

```python
from app.core.languages import is_supported_language  # add at top with other imports


class UpdateLanguageRequest(BaseModel):
    language: str

    @field_validator("language")
    @classmethod
    def language_supported(cls, v: str) -> str:
        if not is_supported_language(v):
            raise ValueError("unsupported language")
        return v
```

> Ensure `from pydantic import BaseModel, field_validator` is imported at the top of `schemas/user.py` (add `field_validator` if missing). A `ValueError` in a Pydantic validator surfaces as HTTP 422.

- [ ] **Step 7: Add the endpoint**

In `backend/app/routers/users.py`, add after `update_preferences` (import `UpdateLanguageRequest` in the existing schemas import line):

```python
@router.patch("/me/language", response_model=UserProfile)
async def update_language(
    payload: UpdateLanguageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Dedicated, validated surface for the language switcher (kept separate from
    # the broad preferences PATCH so it has one small, well-tested contract).
    current_user.language = payload.language
    await session.commit()
    await session.refresh(current_user)
    profile = UserProfile.model_validate(current_user)
    profile.is_parent = await _is_parent(session, current_user)
    return profile
```

- [ ] **Step 8: Run the tests + lint**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_user_language.py -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/`
Expected: PASS (3 passed); ruff clean.

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/user.py backend/alembic/versions/a1b2c3d4e5f6_user_language.py backend/app/schemas/user.py backend/app/routers/users.py backend/tests/test_user_language.py
git commit -m "feat(i18n): user.language column + PATCH /users/me/language"
```

---

### Task 3: Frontend deps + i18next init + provider wiring

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/i18n/index.ts`
- Create: `frontend/src/locales/en/common.json` (seed namespace so init has resources)
- Modify: `frontend/src/main.tsx`
- Test: `frontend/tests/unit/i18n-init.test.tsx`

- [ ] **Step 1: Add dependencies**

Run: `cd frontend && npm install i18next@^25 react-i18next@^15 @capacitor/device@^8`
Expected: `package.json` + lockfile updated. (Versions: align majors with the installed React 18 / Capacitor 8; if `npm` resolves a different compatible major, accept it and note it in the commit.)

- [ ] **Step 2: Write the failing test**

Create `frontend/tests/unit/i18n-init.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import { describe, expect, it } from 'vitest';
import { useTranslation } from 'react-i18next';
import { i18n, initI18n } from '../../src/i18n';

function Probe() {
  const { t } = useTranslation();
  return <span>{t('common.appName')}</span>;
}

describe('i18n init', () => {
  it('renders a key from the en catalog', async () => {
    await initI18n('en');
    render(
      <I18nextProvider i18n={i18n}>
        <Probe />
      </I18nextProvider>,
    );
    expect(screen.getByText('InvestiKid')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run it to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/i18n-init.test.tsx`
Expected: FAIL (cannot resolve `../../src/i18n`).

- [ ] **Step 4: Seed the first catalog**

Create `frontend/src/locales/en/common.json`:

```json
{
  "appName": "InvestiKid",
  "language": {
    "label": "Language",
    "help": "More languages are coming soon."
  }
}
```

- [ ] **Step 5: Implement the i18n init**

Create `frontend/src/i18n/index.ts`:

```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import type { LanguageCode } from './languages';

// Lazy-load a language's namespaces so future catalogs don't bloat the initial
// bundle. Only namespaces that exist for a language are imported.
const NAMESPACES = ['common'] as const;

async function loadCatalog(lng: LanguageCode): Promise<Record<string, unknown>> {
  const entries = await Promise.all(
    NAMESPACES.map(async (ns) => {
      try {
        const mod = await import(`../locales/${lng}/${ns}.json`);
        return [ns, mod.default] as const;
      } catch {
        return [ns, {}] as const;
      }
    }),
  );
  return Object.fromEntries(entries);
}

export async function initI18n(lng: LanguageCode): Promise<void> {
  const resources = { [lng]: await loadCatalog(lng) };
  if (lng !== 'en') {
    resources.en = await loadCatalog('en'); // fallback catalog
  }
  await i18n.use(initReactI18next).init({
    lng,
    fallbackLng: 'en',
    ns: [...NAMESPACES],
    defaultNS: 'common',
    resources,
    interpolation: { escapeValue: false },
    returnNull: false,
  });
}

export async function changeLanguage(lng: LanguageCode): Promise<void> {
  if (!i18n.hasResourceBundle(lng, 'common')) {
    const catalog = await loadCatalog(lng);
    for (const [ns, bundle] of Object.entries(catalog)) {
      i18n.addResourceBundle(lng, ns, bundle, true, true);
    }
  }
  await i18n.changeLanguage(lng);
}

export { i18n };
```

> Vite supports dynamic `import()` with template literals via glob; if the build warns about the dynamic path, add an explicit glob (`import.meta.glob('../locales/*/*.json')`) and resolve from it. Keep the public `initI18n`/`changeLanguage` signatures unchanged.

- [ ] **Step 6: Wire it into main.tsx**

In `frontend/src/main.tsx`, before `ReactDOM.createRoot(...).render(...)`, resolve the boot language and init i18n, then wrap the tree. Minimal change:

```typescript
import { I18nextProvider } from 'react-i18next';
import { i18n, initI18n } from './i18n';
import { resolveBootLanguage } from './i18n/resolveLanguage';

async function bootstrap() {
  await initI18n(await resolveBootLanguage());
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <I18nextProvider i18n={i18n}>
      {/* existing provider tree (BrowserRouter > QueryClientProvider > App) unchanged */}
    </I18nextProvider>,
  );
}

void bootstrap();
```

> Preserve the existing `PersistQueryClientProvider`/`BrowserRouter`/`App` subtree exactly — only wrap it with `<I18nextProvider>` and move the render into `bootstrap()`. `resolveBootLanguage` is created in Task 6; until then, temporarily call `initI18n('en')` and replace in Task 6.

- [ ] **Step 7: Run the test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/i18n-init.test.tsx`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/i18n/index.ts frontend/src/locales/en/common.json frontend/src/main.tsx frontend/tests/unit/i18n-init.test.tsx
git commit -m "feat(i18n): react-i18next runtime + lazy catalogs + provider wiring"
```

---

### Task 4: Frontend user language type + API + useLanguage hook

**Files:**
- Modify: `frontend/src/api/auth.ts` (Me type ~line 7; authApi ~line 54)
- Create: `frontend/src/hooks/useLanguage.ts`
- Test: `frontend/tests/unit/useLanguage.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/useLanguage.test.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../../src/api/auth', () => ({
  authApi: { updateLanguage: vi.fn().mockResolvedValue({ language: 'es' }) },
}));
vi.mock('../../src/i18n', () => ({ changeLanguage: vi.fn().mockResolvedValue(undefined) }));

import { authApi } from '../../src/api/auth';
import { changeLanguage } from '../../src/i18n';
import { useLanguage } from '../../src/hooks/useLanguage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient();
  qc.setQueryData(['me'], { language: 'en' });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useLanguage', () => {
  beforeEach(() => localStorage.clear());

  it('reads current language from the cached profile', () => {
    const { result } = renderHook(() => useLanguage(), { wrapper });
    expect(result.current.current).toBe('en');
  });

  it('setLanguage updates i18n, localStorage and the server', async () => {
    const { result } = renderHook(() => useLanguage(), { wrapper });
    await act(async () => {
      await result.current.setLanguage('es');
    });
    expect(changeLanguage).toHaveBeenCalledWith('es');
    expect(localStorage.getItem('language')).toBe('es');
    await waitFor(() => expect(authApi.updateLanguage).toHaveBeenCalledWith('es'));
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/useLanguage.test.tsx`
Expected: FAIL (no `useLanguage`, no `authApi.updateLanguage`).

- [ ] **Step 3: Extend the Me type + API**

In `frontend/src/api/auth.ts`, add to the `Me` type (after `currency_code`):

```typescript
  language?: string;
```

And add to `authApi` (mirroring `updatePreferences`):

```typescript
  updateLanguage: (language: string) =>
    apiFetch<Me>('/users/me/language', {
      method: 'PATCH',
      body: JSON.stringify({ language }),
    }),
```

- [ ] **Step 4: Implement the hook**

Create `frontend/src/hooks/useLanguage.ts`:

```typescript
import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import type { Me } from '../api/auth';
import { authApi } from '../api/auth';
import { changeLanguage } from '../i18n';
import { type LanguageCode, isSupportedLanguage } from '../i18n/languages';

export const LANGUAGE_STORAGE_KEY = 'language';

export function useLanguage() {
  const qc = useQueryClient();
  const me = qc.getQueryData<Me>(['me']);
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  const current: LanguageCode =
    (me?.language && isSupportedLanguage(me.language) && me.language) ||
    (stored && isSupportedLanguage(stored) && stored) ||
    'en';

  const setLanguage = useCallback(
    async (lng: LanguageCode) => {
      await changeLanguage(lng); // instant UI swap
      localStorage.setItem(LANGUAGE_STORAGE_KEY, lng); // fast boot next time
      qc.setQueryData<Me | undefined>(['me'], (prev) =>
        prev ? { ...prev, language: lng } : prev,
      );
      try {
        await authApi.updateLanguage(lng); // server = source of truth
      } catch {
        // keep the local change; server reconciles on next /me load
      }
    },
    [qc],
  );

  return { current, setLanguage };
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/useLanguage.test.tsx`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/auth.ts frontend/src/hooks/useLanguage.ts frontend/tests/unit/useLanguage.test.tsx
git commit -m "feat(i18n): Me.language + useLanguage hook (server+localStorage+i18n)"
```

---

### Task 5: LanguageSwitcher component + mount in child & parent settings

**Files:**
- Create: `frontend/src/components/settings/LanguageSwitcher.tsx`
- Modify: `frontend/src/components/child/ProfileMenu.tsx` (after `CurrencySelector`, ~line 194)
- Modify: `frontend/src/pages/ParentDashboard.tsx`
- Test: `frontend/src/components/settings/__tests__/LanguageSwitcher.test.tsx`

- [ ] **Step 1: Write the failing test (incl. a11y)**

Create `frontend/src/components/settings/__tests__/LanguageSwitcher.test.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { LanguageSwitcher } from '../LanguageSwitcher';

vi.mock('../../../hooks/useLanguage', () => ({
  useLanguage: () => ({ current: 'en', setLanguage: vi.fn() }),
}));

function wrapper(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe('LanguageSwitcher', () => {
  it('renders a labelled control listing only available languages', () => {
    render(wrapper(<LanguageSwitcher />));
    const select = screen.getByLabelText(/language/i);
    expect(select).toBeInTheDocument();
    // English only at launch
    expect(screen.getByRole('option', { name: 'English' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Español' })).not.toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrapper(<LanguageSwitcher />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/components/settings/__tests__/LanguageSwitcher.test.tsx`
Expected: FAIL (no `LanguageSwitcher`).

- [ ] **Step 3: Implement the component** (mirror `RegionSwitcher.tsx` structure)

Create `frontend/src/components/settings/LanguageSwitcher.tsx`:

```typescript
import { useTranslation } from 'react-i18next';
import { useLanguage } from '../../hooks/useLanguage';
import { AVAILABLE_LANGUAGES, type LanguageCode } from '../../i18n/languages';

export function LanguageSwitcher() {
  const { t } = useTranslation();
  const { current, setLanguage } = useLanguage();

  return (
    <div className="space-y-1.5">
      <label htmlFor="settings-language" className="text-sm font-medium">
        {t('common.language.label')}
      </label>
      <select
        id="settings-language"
        value={current}
        onChange={(e) => void setLanguage(e.target.value as LanguageCode)}
        className="min-h-[44px] w-full rounded-lg border px-3 text-base"
      >
        {AVAILABLE_LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.endonym}
          </option>
        ))}
      </select>
      <p className="text-xs text-muted-foreground">{t('common.language.help')}</p>
    </div>
  );
}
```

> `text-base` keeps the control ≥16px on iOS (no zoom). The 44px min height meets the touch-target rule.

- [ ] **Step 4: Mount in child settings**

In `frontend/src/components/child/ProfileMenu.tsx`, import and render `<LanguageSwitcher />` immediately after the `CurrencySelector` (~line 194):

```typescript
import { LanguageSwitcher } from '../settings/LanguageSwitcher';
// ...inside the Preferences section, after <CurrencySelector .../>:
<LanguageSwitcher />
```

- [ ] **Step 5: Mount in parent settings**

In `frontend/src/pages/ParentDashboard.tsx`, render `<LanguageSwitcher />` within the parent's settings/preferences area (place it near the top of the dashboard's account/settings block; import as `import { LanguageSwitcher } from '../components/settings/LanguageSwitcher';`).

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd frontend && npx vitest run src/components/settings/__tests__/LanguageSwitcher.test.tsx`
Expected: PASS (2 passed, no a11y violations).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/settings/LanguageSwitcher.tsx frontend/src/components/child/ProfileMenu.tsx frontend/src/pages/ParentDashboard.tsx frontend/src/components/settings/__tests__/LanguageSwitcher.test.tsx
git commit -m "feat(i18n): LanguageSwitcher in child + parent settings"
```

---

### Task 6: Boot language resolution (device-locale default)

**Files:**
- Create: `frontend/src/i18n/resolveLanguage.ts`
- Modify: `frontend/src/main.tsx` (replace the temporary `initI18n('en')` with `resolveBootLanguage()`)
- Test: `frontend/tests/unit/resolveLanguage.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/resolveLanguage.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from 'vitest';
import { mapToSupported } from '../../src/i18n/resolveLanguage';

describe('mapToSupported', () => {
  it('maps exact codes', () => {
    expect(mapToSupported('en')).toBe('en');
    expect(mapToSupported('de')).toBe('de');
  });
  it('maps regioned locales to the base language', () => {
    expect(mapToSupported('es-ES')).toBe('es');
    expect(mapToSupported('fr-CA')).toBe('fr');
  });
  it('maps Chinese scripts correctly', () => {
    expect(mapToSupported('zh-Hant-HK')).toBe('zh-Hant');
    expect(mapToSupported('zh-TW')).toBe('zh-Hant');
    expect(mapToSupported('zh-CN')).toBe('zh-Hans');
    expect(mapToSupported('zh')).toBe('zh-Hans');
  });
  it('falls back to English for unsupported', () => {
    expect(mapToSupported('ja')).toBe('en');
    expect(mapToSupported('')).toBe('en');
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/resolveLanguage.test.ts`
Expected: FAIL (no `mapToSupported`).

- [ ] **Step 3: Implement resolution**

Create `frontend/src/i18n/resolveLanguage.ts`:

```typescript
import { type LanguageCode, isSupportedLanguage } from './languages';
import { LANGUAGE_STORAGE_KEY } from '../hooks/useLanguage';
import { isNativeApp } from '../lib/platform';

// Map an arbitrary BCP-47 locale to one of our supported codes.
export function mapToSupported(locale: string): LanguageCode {
  const lc = (locale || '').toLowerCase();
  if (lc.startsWith('zh')) {
    // Traditional: Hant, TW, HK, MO; everything else Chinese → Simplified.
    if (lc.includes('hant') || lc.includes('-tw') || lc.includes('-hk') || lc.includes('-mo')) {
      return 'zh-Hant';
    }
    return 'zh-Hans';
  }
  const base = lc.split('-')[0];
  return isSupportedLanguage(base) ? (base as LanguageCode) : 'en';
}

async function deviceLocale(): Promise<string> {
  if (isNativeApp()) {
    try {
      const { Device } = await import('@capacitor/device');
      const { value } = await Device.getLanguageTag();
      return value;
    } catch {
      /* fall through to navigator */
    }
  }
  return navigator.language || 'en';
}

// Boot order: localStorage cache → device locale → en. (The authenticated
// server value overrides this once /me loads; see useLanguage.)
export async function resolveBootLanguage(): Promise<LanguageCode> {
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored && isSupportedLanguage(stored)) return stored;
  return mapToSupported(await deviceLocale());
}
```

- [ ] **Step 4: Use it in main.tsx**

Replace the temporary `await initI18n('en')` in `frontend/src/main.tsx` with:

```typescript
await initI18n(await resolveBootLanguage());
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/resolveLanguage.test.ts`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/i18n/resolveLanguage.ts frontend/src/main.tsx frontend/tests/unit/resolveLanguage.test.ts
git commit -m "feat(i18n): boot language resolution with device-locale default"
```

---

## PHASE 2 — Extraction tooling + completeness guard

### Task 7: Pseudo-locale generator + extraction-proof test

**Files:**
- Create: `frontend/scripts/gen-pseudo-locale.mjs`
- Modify: `frontend/package.json` (scripts)
- Test: `frontend/tests/unit/pseudo-locale.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/unit/pseudo-locale.test.tsx`:

```typescript
import { describe, expect, it } from 'vitest';
import { pseudo } from '../../scripts/pseudo-transform.mjs';

describe('pseudo-locale transform', () => {
  it('accents and brackets a string so untranslated text is obvious', () => {
    const out = pseudo('Home');
    expect(out).not.toBe('Home');
    expect(out.startsWith('[')).toBe(true);
    expect(out).toMatch(/[^\x00-\x7F]/); // contains non-ASCII accents
  });
  it('preserves interpolation placeholders', () => {
    expect(pseudo('You earned {{count}} XP')).toContain('{{count}}');
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run tests/unit/pseudo-locale.test.tsx`
Expected: FAIL (no `pseudo-transform.mjs`).

- [ ] **Step 3: Implement the transform + generator**

Create `frontend/scripts/pseudo-transform.mjs`:

```javascript
const MAP = { a: 'ä', e: 'ё', i: 'ï', o: 'ö', u: 'ü', A: 'Ä', E: 'Ё', O: 'Ö' };

// Transform a single string, leaving {{interpolation}} and <Trans> tags intact.
export function pseudo(s) {
  let out = '';
  let i = 0;
  while (i < s.length) {
    if (s.startsWith('{{', i)) {
      const end = s.indexOf('}}', i);
      out += s.slice(i, end + 2);
      i = end + 2;
      continue;
    }
    out += MAP[s[i]] ?? s[i];
    i += 1;
  }
  return `[${out}]`;
}

export function pseudoTree(obj) {
  if (typeof obj === 'string') return pseudo(obj);
  const out = {};
  for (const [k, v] of Object.entries(obj)) out[k] = pseudoTree(v);
  return out;
}
```

Create `frontend/scripts/gen-pseudo-locale.mjs`:

```javascript
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pseudoTree } from './pseudo-transform.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const enDir = join(here, '..', 'src', 'locales', 'en');
const xaDir = join(here, '..', 'src', 'locales', 'en-XA');
mkdirSync(xaDir, { recursive: true });
for (const f of readdirSync(enDir).filter((n) => n.endsWith('.json'))) {
  const src = JSON.parse(readFileSync(join(enDir, f), 'utf-8'));
  writeFileSync(join(xaDir, f), JSON.stringify(pseudoTree(src), null, 2));
}
console.log('Generated en-XA pseudo-locale.');
```

Add to `frontend/package.json` scripts:

```json
"i18n:pseudo": "node scripts/gen-pseudo-locale.mjs"
```

> `en-XA` is dev/test only and never added to `SUPPORTED_LANGUAGES`, so it can't be selected by users.

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npx vitest run tests/unit/pseudo-locale.test.tsx`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/scripts/pseudo-transform.mjs frontend/scripts/gen-pseudo-locale.mjs frontend/package.json frontend/tests/unit/pseudo-locale.test.tsx
git commit -m "feat(i18n): pseudo-locale generator + transform tests"
```

---

### Task 8: ESLint `no-literal-string` completeness guard (warn → error later)

**Files:**
- Modify: `frontend/package.json` (dep)
- Modify: `frontend/eslint.config.js`

- [ ] **Step 1: Add the plugin**

Run: `cd frontend && npm install -D eslint-plugin-i18next`
Expected: devDependency added.

- [ ] **Step 2: Configure the rule as a WARNING first**

In `frontend/eslint.config.js`, add the plugin and rule. Start at `warn` so the (still-unextracted) codebase lints without blocking, and so the extraction tasks can drive the warning count to zero:

```javascript
import i18next from 'eslint-plugin-i18next';

// ...inside the main config object's plugins:
'i18next': i18next,
// ...inside rules:
'i18next/no-literal-string': ['warn', {
  mode: 'jsx-text-only',
  'jsx-attributes': { include: ['alt', 'aria-label', 'placeholder', 'title'] },
}],
// Tests and scripts are exempt:
```

Add an override so tests/scripts/locale files are exempt:

```javascript
{ files: ['tests/**', 'scripts/**', 'src/locales/**', '**/__tests__/**'], rules: { 'i18next/no-literal-string': 'off' } },
```

- [ ] **Step 3: Confirm the rule reports the current hardcoded strings**

Run: `cd frontend && npx eslint src --rule '{}' 2>&1 | grep -c 'no-literal-string' || true`
Expected: a large non-zero count (the strings still to extract). This proves the guard sees them.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/eslint.config.js
git commit -m "chore(i18n): add no-literal-string guard (warn) to drive extraction"
```

---

## PHASE 3 — Full extraction

> Extraction is mechanical and large (~273 components). Do it in **parallel batches by directory area**, each batch an independent task following the identical procedure below and gated by the guard reaching **zero warnings for that area**. Task 9 is the worked example that locks the procedure; Tasks 10–17 apply it per area; Task 18 flips the guard to `error` and verifies.

**Per-file extraction procedure (the convention):**
1. For each user-facing literal in JSX text or a guarded attribute (`alt`, `aria-label`, `placeholder`, `title`), choose a namespaced key: `<area>.<screen>.<element>` (e.g. `lessons.list.title`). One namespace JSON per area under `src/locales/en/<area>.json`; register new namespaces in `NAMESPACES` in `src/i18n/index.ts`.
2. Add the English text as the key's value in that namespace file.
3. Replace the literal with `t('<area>.<key>')` (call `const { t } = useTranslation('<area>')` or use the default namespace with a fully-qualified key). For embedded values use interpolation: `t('xp.earned', { count })` + `"earned": "You earned {{count}} XP"`. For count-plurals use i18next plural keys (`key_one`/`key_other`). For inline markup/links use `<Trans i18nKey=...>`.
4. Leave genuinely non-translatable tokens (the brand name "InvestiKid", pure numerals, emoji/icons) — they're covered by the rule's allowlist or are not text nodes.
5. Run the area lint + the area's tests; the area must reach **zero** `no-literal-string` warnings.

### Task 9: Worked example — extract `ProfileMenu.tsx` (locks the convention)

**Files:**
- Create: `frontend/src/locales/en/settings.json`
- Modify: `frontend/src/i18n/index.ts` (add `'settings'` to `NAMESPACES`)
- Modify: `frontend/src/components/child/ProfileMenu.tsx`
- Test: `frontend/src/components/child/__tests__/ProfileMenu.i18n.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/child/__tests__/ProfileMenu.i18n.test.tsx`:

```typescript
import { describe, expect, it } from 'vitest';
import en from '../../../locales/en/settings.json';

// Guards that the representative strings were moved into the catalog (not the
// component). If someone re-inlines copy, this catches the regression.
describe('ProfileMenu i18n catalog', () => {
  it('contains the extracted preference strings', () => {
    expect(en).toMatchObject({
      sounds: { label: 'Sounds' },
      dailyGoal: { legend: 'Daily goal' },
    });
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && npx vitest run src/components/child/__tests__/ProfileMenu.i18n.test.tsx`
Expected: FAIL (no `settings.json`).

- [ ] **Step 3: Create the namespace + register it**

Create `frontend/src/locales/en/settings.json`:

```json
{
  "interestArea": "Interest area",
  "sounds": { "label": "Sounds", "help": "Fun little sound effects when you learn and trade. On by default." },
  "dailyGoal": { "legend": "Daily goal" },
  "shop": { "label": "Penny's Shop" },
  "startFresh": "Start fresh",
  "reminders": { "streak": "Daily streak reminder", "alerts": "Streak alerts from InvestiKid" },
  "faceId": "Sign in with Face ID"
}
```

In `frontend/src/i18n/index.ts`, extend: `const NAMESPACES = ['common', 'settings'] as const;`

- [ ] **Step 4: Replace literals in ProfileMenu.tsx**

Add `import { useTranslation } from 'react-i18next';`, `const { t } = useTranslation('settings');`, and replace each literal per the procedure, e.g.:

```typescript
<span>{t('sounds.label')}</span>
<p id="sound-help" className="text-xs text-muted-foreground">{t('sounds.help')}</p>
<legend className="text-sm font-medium">{t('dailyGoal.legend')}</legend>
```

(Repeat for `interestArea`, `shop.label`, `startFresh`, `reminders.*`, `faceId`.)

- [ ] **Step 5: Verify tests + guard for this file**

Run: `cd frontend && npx vitest run src/components/child/__tests__/ProfileMenu.i18n.test.tsx && npx eslint src/components/child/ProfileMenu.tsx 2>&1 | grep -c no-literal-string || true`
Expected: test PASS; literal count `0` for this file.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/locales/en/settings.json frontend/src/i18n/index.ts frontend/src/components/child/ProfileMenu.tsx frontend/src/components/child/__tests__/ProfileMenu.i18n.test.tsx
git commit -m "feat(i18n): extract ProfileMenu strings (worked example + convention)"
```

### Tasks 10–17: Batched extraction by area (parallelizable)

Apply the **per-file extraction procedure** to each area below. Each is an independent task: create/extend `src/locales/en/<area>.json`, register the namespace, replace literals, drive `no-literal-string` to **0** for that area's paths, run that area's existing tests, commit `feat(i18n): extract <area> strings`.

- [ ] **Task 10 — `auth`:** `src/pages/child/Login*`, `Signup*`, `src/pages/ParentLogin.tsx`, `ForgotPassword.tsx`, `ResetPassword.tsx`, `VerifyEmail.tsx`, `ConsentVerify.tsx` → `en/auth.json`.
- [ ] **Task 11 — `home`:** `src/pages/child/Home.tsx` + Home sub-components (HomeHero, StatsCard, QuickLinksRow, ReviseCard, etc.) → `en/home.json`.
- [ ] **Task 12 — `lessons`:** `src/pages/child/Lessons.tsx`, lesson player + quiz/scenario/card renderers → `en/lessons.json`.
- [ ] **Task 13 — `revise`:** `src/pages/child/Revise*` + Revise components → `en/revise.json`.
- [ ] **Task 14 — `simulator`:** `src/pages/child/Simulator*`, stock pages, holdings/history, chart coach → `en/simulator.json`.
- [ ] **Task 15 — `child-shared`:** remaining `src/components/child/**` (nav/BottomTabBar, OptionCard labels, shop, cosmetics, gamification, toasts) → `en/child.json`.
- [ ] **Task 16 — `parent`:** `src/pages/ParentDashboard.tsx`, `ParentAuthCallback.tsx`, parent components, `Privacy.tsx`, `Try.tsx` → `en/parent.json`.
- [ ] **Task 17 — `admin` + `ui`:** `src/pages/admin/**`, `AdminSettings.tsx`, shared `src/components/ui/**` literals → `en/admin.json`, `en/ui.json`.

> Subagent dispatch note (for the controller): these 8 tasks touch disjoint directories and can run as parallel subagents. Each subagent gets this procedure + its area's file list + the convention from Task 9. Reconcile namespace registration (`NAMESPACES` in `src/i18n/index.ts`) in a single follow-up commit if parallel edits collide there.

### Task 18: Flip the guard to error + full verification

**Files:**
- Modify: `frontend/eslint.config.js`

- [ ] **Step 1: Confirm zero literals remain**

Run: `cd frontend && npx eslint src 2>&1 | grep -c no-literal-string || true`
Expected: `0`. (If non-zero, extract the remaining files before proceeding — do not allowlist real copy.)

- [ ] **Step 2: Flip the rule to error**

In `frontend/eslint.config.js`, change `'i18next/no-literal-string'` severity from `'warn'` to `'error'` so CI fails on any future un-extracted string.

- [ ] **Step 3: Pseudo-locale sweep (visual completeness proof)**

Run: `cd frontend && npm run i18n:pseudo && npx tsc -b`
Then temporarily boot with `en-XA` (set `localStorage.language = 'en-XA'` in a dev run, or add a throwaway `initI18n('en-XA')`), load the main screens, and confirm **all** visible copy is accented/bracketed (any plain English = a missed string). Revert the throwaway boot change. Delete `src/locales/en-XA` before committing (it's generated, not shipped).

- [ ] **Step 4: Full frontend verification**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green (lint now enforces `no-literal-string` as error; full vitest suite incl. vitest-axe passes; build succeeds).

- [ ] **Step 5: Commit**

```bash
git add frontend/eslint.config.js
git commit -m "chore(i18n): enforce no-literal-string (error) after full extraction"
```

---

### Task 19: Backend verify + iOS sync + promote

- [ ] **Step 1: Backend verification**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
Expected: ruff clean; full suite passes.

- [ ] **Step 2: iOS sync (UI-visible change)**

Run: `cd frontend && npm run build && npx cap sync ios`
Then rebuild in Xcode and confirm the Settings language control renders/persists in the WKWebView (≥16px, no zoom on focus).

- [ ] **Step 3: Push to testing + green CI**

```bash
git push origin testing
```
Watch all 6 CI jobs go green (Detect, Backend, Security, Frontend, A11y, Responsive).

- [ ] **Step 4: Promote testing → staging → main**

Merge testing → staging (watch CI green), then staging → main (watch CI green; Railway deploys backend on green main). **This carries a DB migration — before it reaches prod, ask the user whether to snapshot the prod DB first** (standing rule). After deploy, confirm prod `/health` 200 and that `/users/me` returns `language: "en"`.

---

## Self-Review

**Spec coverage:**
- Registry (shared, parity) → Task 1. ✓
- `User.language` column + additive migration + `/me` field + validated `PATCH /me/language` → Task 2. ✓
- i18next runtime, lazy catalogs, fallback en, provider at root, key convention → Tasks 3, 9 (convention). ✓
- Full English extraction → Tasks 9–18. ✓
- Pseudo-locale + lint guard completeness proof → Tasks 7, 8, 18. ✓
- Preference wiring (server source of truth, localStorage cache, device-locale default) → Tasks 4, 6. ✓
- Switcher in child + parent, available-only, a11y, ≥16px → Task 5. ✓
- Non-goals (no real translations, no RTL, no AI/curriculum/currency) → respected (only `en` catalog; no formatting changes). ✓
- iOS sync; promote with snapshot prompt → Task 19. ✓
- Definition of done (drop-in catalog flips UI) → satisfied by the namespace/lazy-load design + guard; verifiable by adding any `<lng>` catalog.

**Placeholder scan:** No TBD/TODO; infra tasks carry full code; extraction tasks carry the exact procedure + a worked example (Task 9) rather than 273 enumerated files (mechanical bulk — completeness enforced by the guard, not by enumeration).

**Type/name consistency:** `initI18n`/`changeLanguage`/`i18n` (Task 3) reused in Tasks 4/6; `useLanguage().{current,setLanguage}` (Task 4) consumed in Task 5; `LANGUAGE_STORAGE_KEY` defined in Task 4, imported in Task 6; `mapToSupported`/`resolveBootLanguage` (Task 6) used in `main.tsx`; `is_supported_language` (Task 1) used by `UpdateLanguageRequest` (Task 2); `UserProfile.language` (Task 2) surfaced as `Me.language` (Task 4). Consistent.
