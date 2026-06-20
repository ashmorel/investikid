# Pre-TestFlight Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep users logged in safely (silent refresh), keep premium entitlement honest (period guard + reconcile), and get the streak reminder enabled (one-time native nudge).

**Architecture:** Three independent units. Unit 1 is frontend-only (refresh-on-401 in `apiFetch`; backend `/auth/refresh` already exists). Unit 2 is backend-only (a `current_period_end` guard in `recompute_household_premium` + a daily reconcile cron that re-pulls provider state). Unit 3 is frontend-only (a native one-time nudge reusing the existing reminder lib). No DB migration.

**Tech Stack:** React 18 + Vite + TS + vitest (frontend); FastAPI + SQLAlchemy 2.0 async + pytest (backend); GitHub Actions cron.

**Spec:** `docs/superpowers/specs/2026-06-20-pre-testflight-hardening-design.md`
**Branch:** `testing`. No migration → no snapshot question.

---

## File structure

- `frontend/src/api/client.ts` — MODIFY: add single-flight refresh-on-401 + retry-once.
- `frontend/src/api/__tests__/client.test.ts` — CREATE: client tests.
- `backend/app/services/entitlements.py` — MODIFY: `current_period_end` guard in `recompute_household_premium`.
- `backend/tests/test_entitlements_freshness.py` — CREATE: entitlement truth-table.
- `backend/app/services/subscription_reconcile_service.py` — CREATE: daily reconcile.
- `backend/app/routers/internal.py` — MODIFY: add `/internal/subscriptions/reconcile`.
- `.github/workflows/video-health-cron.yml` — MODIFY: add the reconcile endpoint to the loop.
- `backend/tests/test_subscription_reconcile.py` — CREATE: reconcile tests.
- `frontend/src/components/child/StreakReminderNudge.tsx` — CREATE: the nudge.
- `frontend/src/pages/child/Home.tsx` — MODIFY: render the nudge.
- `frontend/src/components/child/__tests__/StreakReminderNudge.test.tsx` — CREATE: nudge tests.
- `frontend/src/locales/en/<home-namespace>.json` — MODIFY: nudge strings.

---

### Task 1: Unit 1 — Persistent login (refresh-on-401)

**Files:** Modify `frontend/src/api/client.ts`; Create `frontend/src/api/__tests__/client.test.ts`.

Current `apiFetch` (read it first) builds headers, does ONE `fetch`, and throws `ApiError` on `!res.ok`. We add: on a `401` for a non-auth path, do a **single-flight** `POST /auth/refresh`, and if it succeeds **retry the original request once** (rebuilding headers so a rotated CSRF cookie is picked up).

- [ ] **Step 1: Write the failing test** — `frontend/src/api/__tests__/client.test.ts`:

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiFetch, ApiError } from '../client';

function jsonRes(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: String(status),
    json: async () => body,
  } as Response;
}

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  document.cookie = '';
});

describe('apiFetch refresh-on-401', () => {
  it('refreshes then retries once on 401, returning the retried body', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonRes(401, { detail: 'expired' }))   // original
      .mockResolvedValueOnce(jsonRes(200, { ok: true }))            // /auth/refresh
      .mockResolvedValueOnce(jsonRes(200, { data: 42 }));           // retry
    const out = await apiFetch<{ data: number }>('/users/me');
    expect(out).toEqual({ data: 42 });
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls.filter((u) => u.endsWith('/auth/refresh'))).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('shares ONE refresh across concurrent 401s (single-flight)', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (String(url).endsWith('/auth/refresh')) return jsonRes(200, { ok: true });
      // first call per path 401s, subsequent (retry) succeeds
      return jsonRes(200, { data: 1 });
    });
    // two parallel calls that both 401 first
    let firstA = true, firstB = true;
    fetchMock.mockImplementation(async (url: string) => {
      const u = String(url);
      if (u.endsWith('/auth/refresh')) return jsonRes(200, { ok: true });
      if (u.endsWith('/a')) { if (firstA) { firstA = false; return jsonRes(401, { detail: 'x' }); } return jsonRes(200, { p: 'a' }); }
      if (firstB) { firstB = false; return jsonRes(401, { detail: 'x' }); } return jsonRes(200, { p: 'b' });
    });
    const [a, b] = await Promise.all([apiFetch('/a'), apiFetch('/b')]);
    expect(a).toEqual({ p: 'a' });
    expect(b).toEqual({ p: 'b' });
    const refreshes = fetchMock.mock.calls.filter((c) => String(c[0]).endsWith('/auth/refresh'));
    expect(refreshes).toHaveLength(1);
  });

  it('throws the original 401 when refresh fails (no loop)', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonRes(401, { detail: 'expired' }))  // original
      .mockResolvedValueOnce(jsonRes(401, { detail: 'no rt' }));   // /auth/refresh fails
    await expect(apiFetch('/users/me')).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(2); // no retry
  });

  it('does not refresh for auth endpoints themselves', async () => {
    fetchMock.mockResolvedValueOnce(jsonRes(401, { detail: 'bad creds' }));
    await expect(apiFetch('/auth/login', { method: 'POST', body: '{}' })).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1); // no /auth/refresh
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npx vitest run src/api/__tests__/client.test.ts` → FAIL (no refresh logic yet; concurrent + retry expectations unmet).

- [ ] **Step 3: Implement** — replace `frontend/src/api/client.ts` body of `apiFetch` and add the refresh helper. Full file:

```ts
import { readCookie } from '@/lib/cookies';
import { isNativeApp } from '@/lib/platform';

const NATIVE_API_FALLBACK = 'https://investikid.up.railway.app';

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL || (isNativeApp() ? NATIVE_API_FALLBACK : '');

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public code?: string,
    public context?: unknown,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

// Paths that must never trigger a refresh attempt (they ARE the auth surface).
const AUTH_PATHS = ['/auth/refresh', '/auth/login', '/auth/register'];
function isAuthPath(path: string): boolean {
  return AUTH_PATHS.some((p) => path.startsWith(p));
}

function mutatingHeaders(method: string, extra?: HeadersInit): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((extra as Record<string, string>) ?? {}),
  };
  if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') {
    const csrf = readCookie('csrf_token');
    if (csrf) headers['X-CSRF-Token'] = csrf;
    if (isNativeApp()) headers['X-Capacitor-App'] = '1';
  }
  return headers;
}

// Single-flight token refresh: concurrent 401s share one /auth/refresh call.
let refreshInFlight: Promise<boolean> | null = null;
function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: mutatingHeaders('POST'),
        });
        return res.ok;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function apiFetch<T = unknown>(
  path: string,
  init?: RequestInit,
): Promise<T | null> {
  const method = (init?.method ?? 'GET').toUpperCase();
  const doFetch = () =>
    fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      ...init,
      method,
      headers: mutatingHeaders(method, init?.headers),
    });

  let res = await doFetch();
  // Silent session refresh: on a 401 for a non-auth path, refresh once and retry.
  if (res.status === 401 && !isAuthPath(path)) {
    const refreshed = await refreshSession();
    if (refreshed) res = await doFetch();
  }

  if (!res.ok) {
    let detail = res.statusText;
    let code: string | undefined;
    let context: unknown;
    try {
      const body = await res.json();
      const d = body?.detail;
      if (typeof d === 'string') {
        detail = d;
      } else if (d && typeof d === 'object') {
        if (typeof d.message === 'string') detail = d.message;
        if (typeof d.code === 'string') code = d.code;
        context = d.context;
      }
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail, code, context);
  }
  if (res.status === 204) return null;
  return (await res.json()) as T;
}
```

- [ ] **Step 4: Run to verify it passes** — `cd frontend && npx vitest run src/api/__tests__/client.test.ts` → PASS. Then `npx tsc -b && npm run lint` → clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid && git add frontend/src/api/client.ts frontend/src/api/__tests__/client.test.ts && git commit -m "feat(auth): silent refresh-on-401 keeps users logged in

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Unit 2a — Subscription freshness guard

**Files:** Modify `backend/app/services/entitlements.py`; Create `backend/tests/test_entitlements_freshness.py`.

`recompute_household_premium` currently entitles on `status` alone. Add: a row entitles only when `status ∈ ACTIVE_SUBSCRIPTION_STATUSES` **and** (`current_period_end is None` **or** `current_period_end > now`).

- [ ] **Step 1: Write the failing test** — `backend/tests/test_entitlements_freshness.py` (uses `db_session`; copy fixture style from an existing billing/entitlements test). Seed a parent_email with one child + one subscription row, vary status/period, call `recompute_household_premium`, assert `child.is_premium`:

```python
from datetime import UTC, datetime, timedelta

import pytest

from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import recompute_household_premium

pytestmark = pytest.mark.asyncio(loop_scope="session")

PARENT = "freshness-parent@example.com"


async def _seed(db_session, *, status: str, period_end):
    child = User(
        username="fresh-kid", email=None, parent_email=PARENT,
        hashed_password="x", country_code="GB", dob=datetime(2014, 1, 1).date(),
        is_active=True,
    )
    db_session.add(child)
    db_session.add(Subscription(
        parent_email=PARENT, provider="stripe", external_id="sub_fresh",
        status=status, current_period_end=period_end,
    ))
    await db_session.flush()
    return child


async def test_expired_active_row_does_not_entitle(db_session):
    child = await _seed(db_session, status="active",
                        period_end=datetime.now(UTC) - timedelta(days=1))
    await recompute_household_premium(db_session, PARENT)
    assert child.is_premium is False


async def test_future_period_entitles(db_session):
    child = await _seed(db_session, status="active",
                        period_end=datetime.now(UTC) + timedelta(days=10))
    await recompute_household_premium(db_session, PARENT)
    assert child.is_premium is True


async def test_null_period_still_entitles(db_session):
    child = await _seed(db_session, status="active", period_end=None)
    await recompute_household_premium(db_session, PARENT)
    assert child.is_premium is True
```

> Verify the `User` constructor kwargs against `app/models/user.py` before running (required NOT-NULL fields, e.g. `hashed_password`/`country_code`/`dob`); adjust the seed to satisfy them. Match how an existing test (e.g. one under `backend/tests` that creates a `User` + `Subscription`) builds these rows.

- [ ] **Step 2: Run to verify it fails** — `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_entitlements_freshness.py -v` → `test_expired_active_row_does_not_entitle` FAILS (currently entitles on status alone).

- [ ] **Step 3: Implement** — in `backend/app/services/entitlements.py`, add the guard. At the top add the import `from datetime import UTC, datetime`, add a helper, and use it:

```python
def _row_entitles(row: Subscription, now: datetime) -> bool:
    """A subscription row entitles only if its status is active AND its period
    has not passed. A null period (providers that don't populate it) still
    entitles — the daily reconcile re-pulls those from the provider."""
    if row.status not in ACTIVE_SUBSCRIPTION_STATUSES:
        return False
    cpe = row.current_period_end
    if cpe is None:
        return True
    if cpe.tzinfo is None:
        cpe = cpe.replace(tzinfo=UTC)
    return cpe > now
```

Then in `recompute_household_premium` replace the `entitled = any(...)` line with:

```python
    now = datetime.now(UTC)
    entitled = any(_row_entitles(r, now) for r in rows)
```

- [ ] **Step 4: Run to verify it passes** — `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_entitlements_freshness.py -v` → PASS. Run the existing billing/entitlements tests too (e.g. `pytest tests/ -k "entitle or billing or webhook" -q`) → still green. `ruff check .` → clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/entitlements.py backend/tests/test_entitlements_freshness.py && git commit -m "fix(billing): entitlement requires an unexpired subscription period

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Unit 2b — Daily subscription reconcile

**Files:** Create `backend/app/services/subscription_reconcile_service.py`; Modify `backend/app/routers/internal.py`, `.github/workflows/video-health-cron.yml`; Create `backend/tests/test_subscription_reconcile.py`.

A daily cron re-pulls authoritative provider state for at-risk rows (entitling status, period null or at/just-past) so a missed webhook self-heals, then recomputes household premium. Best-effort per row.

- [ ] **Step 1: Write the failing test** — `backend/tests/test_subscription_reconcile.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest

from app.models.subscription import Subscription
from app.models.user import User
from app.services import subscription_reconcile_service as recon

pytestmark = pytest.mark.asyncio(loop_scope="session")

PARENT = "recon-parent@example.com"


async def _seed(db_session, *, provider, external_id, status, period_end):
    child = User(
        username="recon-kid", email=None, parent_email=PARENT, hashed_password="x",
        country_code="GB", dob=datetime(2014, 1, 1).date(), is_active=True, is_premium=True,
    )
    db_session.add(child)
    db_session.add(Subscription(
        parent_email=PARENT, provider=provider, external_id=external_id,
        stripe_subscription_id=external_id if provider == "stripe" else None,
        status=status, current_period_end=period_end,
    ))
    await db_session.flush()
    return child


async def test_reconcile_revokes_a_lapsed_stripe_row(db_session, monkeypatch):
    child = await _seed(db_session, provider="stripe", external_id="sub_dead",
                        status="active", period_end=datetime.now(UTC) - timedelta(hours=1))
    # provider now reports canceled with a past period
    monkeypatch.setattr(recon, "_repull_stripe",
                        lambda sub_id: ("canceled", datetime.now(UTC) - timedelta(hours=1)))
    summary = await recon.run(db_session)
    await db_session.commit()
    assert summary["updated"] >= 1
    assert child.is_premium is False


async def test_reconcile_keeps_an_autorenewed_row(db_session, monkeypatch):
    child = await _seed(db_session, provider="stripe", external_id="sub_live",
                        status="active", period_end=datetime.now(UTC) - timedelta(hours=1))
    # webhook was missed but the sub actually renewed: provider says active + future
    monkeypatch.setattr(recon, "_repull_stripe",
                        lambda sub_id: ("active", datetime.now(UTC) + timedelta(days=20)))
    await recon.run(db_session)
    await db_session.commit()
    assert child.is_premium is True


async def test_one_provider_error_does_not_abort_batch(db_session, monkeypatch):
    good = await _seed(db_session, provider="stripe", external_id="sub_ok",
                       status="active", period_end=datetime.now(UTC) - timedelta(hours=1))
    def boom(_):
        raise RuntimeError("provider down")
    monkeypatch.setattr(recon, "_repull_stripe", boom)
    summary = await recon.run(db_session)
    assert summary["errored"] >= 1
    # the run completed and returned a summary rather than raising
    assert "checked" in summary
```

- [ ] **Step 2: Run to verify it fails** — `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_subscription_reconcile.py -v` → FAIL (module/functions missing).

- [ ] **Step 3: Implement the service** — `backend/app/services/subscription_reconcile_service.py`:

```python
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.services.entitlements import ACTIVE_SUBSCRIPTION_STATUSES, recompute_household_premium

logger = logging.getLogger(__name__)

# Re-check rows whose period ends within this window (or has already passed),
# since those are the ones a missed renewal/cancel webhook would leave stale.
_AT_RISK_WINDOW = timedelta(days=2)


def _repull_stripe(stripe_subscription_id: str) -> tuple[str, datetime | None]:
    """Authoritative (status, current_period_end) from Stripe. Patched in tests."""
    import stripe

    sub = stripe.Subscription.retrieve(stripe_subscription_id)
    end = datetime.fromtimestamp(sub.current_period_end, tz=UTC) if sub.current_period_end else None
    return sub.status, end


def _repull_apple(original_transaction_id: str) -> tuple[str, datetime | None]:
    """Authoritative status from Apple (no period end available here)."""
    from app.services import apple_billing_service

    return apple_billing_service._fetch_status(original_transaction_id), None


def _repull_google(purchase_token: str) -> tuple[str, datetime | None]:
    """Authoritative (status, expiry) from Google Play."""
    from app.services import google_billing_service

    resp = google_billing_service._fetch_subscription(purchase_token)
    return (
        google_billing_service._map_status(resp.get("subscriptionState")),
        google_billing_service._expiry_dt(resp),
    )


def _repull(row: Subscription) -> tuple[str, datetime | None] | None:
    if row.provider == "stripe" and row.stripe_subscription_id:
        return _repull_stripe(row.stripe_subscription_id)
    if row.provider == "apple" and row.external_id:
        return _repull_apple(row.external_id)
    if row.provider == "google" and row.external_id:
        return _repull_google(row.external_id)
    return None  # unknown provider / missing id → skip


async def run(session: AsyncSession) -> dict:
    """Re-pull provider state for at-risk subscription rows and recompute the
    affected households. Best-effort per row; one failure never aborts the run."""
    now = datetime.now(UTC)
    cutoff = now + _AT_RISK_WINDOW
    rows = (await session.scalars(
        select(Subscription).where(
            Subscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
            or_(
                Subscription.current_period_end.is_(None),
                Subscription.current_period_end <= cutoff,
            ),
        )
    )).all()

    checked = updated = errored = 0
    affected: set[str] = set()
    for row in rows:
        checked += 1
        try:
            pulled = _repull(row)
            if pulled is None:
                continue
            status, period_end = pulled
            if status != row.status or period_end != row.current_period_end:
                row.status = status
                if period_end is not None:
                    row.current_period_end = period_end
                updated += 1
            affected.add(row.parent_email)
        except Exception as exc:  # noqa: BLE001 — one bad provider call must not abort the batch
            errored += 1
            logger.warning("reconcile failed for sub %s (%s): %s", row.id, row.provider, exc)

    for parent_email in affected:
        await recompute_household_premium(session, parent_email)

    return {"checked": checked, "updated": updated, "errored": errored}
```

- [ ] **Step 4: Add the internal endpoint** — in `backend/app/routers/internal.py`, add `subscription_reconcile_service` to the `from app.services import ...` line, then add:

```python
@router.post("/subscriptions/reconcile")
async def trigger_subscription_reconcile(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    summary = await subscription_reconcile_service.run(session)
    await session.commit()
    return summary
```

- [ ] **Step 5: Add to the cron loop** — in `.github/workflows/video-health-cron.yml`, add `"internal/subscriptions/reconcile"` to the `endpoints=( ... )` array (one new line alongside the existing internal endpoints).

- [ ] **Step 6: Run to verify it passes** — `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_subscription_reconcile.py -v` → PASS. `ruff check .` → clean. (Verify `_fetch_subscription`/`_map_status`/`_expiry_dt`/`_fetch_status` names against the provider modules before relying on them.)

- [ ] **Step 7: Commit**

```bash
cd /Users/leeashmore/investikid && git add backend/app/services/subscription_reconcile_service.py backend/app/routers/internal.py .github/workflows/video-health-cron.yml backend/tests/test_subscription_reconcile.py && git commit -m "feat(billing): daily subscription reconcile re-pulls provider state

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Unit 3 — Streak-reminder nudge

**Files:** Create `frontend/src/components/child/StreakReminderNudge.tsx`; Modify `frontend/src/pages/child/Home.tsx`, `frontend/src/locales/en/<home-namespace>.json`; Create `frontend/src/components/child/__tests__/StreakReminderNudge.test.tsx`.

A native-only, one-time nudge shown to a child with a live streak who hasn't enabled the reminder, reusing `REMINDER` / `requestReminderPermission` / `syncStreakReminder`.

- [ ] **Step 1: Write the failing test** — `frontend/src/components/child/__tests__/StreakReminderNudge.test.tsx`:

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import StreakReminderNudge from '../StreakReminderNudge';

const isNative = vi.fn(() => true);
const requestPerm = vi.fn(async () => true);
const sync = vi.fn(async () => {});
vi.mock('@/lib/platform', () => ({ isNativeApp: () => isNative() }));
vi.mock('@/lib/streakReminder', () => ({
  requestReminderPermission: () => requestPerm(),
  syncStreakReminder: (a: unknown) => sync(a),
}));
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({ data: { streak_count: 3, last_activity_date: '2020-01-01' } }),
}));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (k: string) => k }) }));

const NUDGE_KEY = 'notif_streak_nudge_seen';
const ENABLED_KEY = 'notif_streak_reminder';

beforeEach(() => {
  localStorage.clear();
  isNative.mockReturnValue(true);
  requestPerm.mockReset().mockResolvedValue(true);
  sync.mockReset();
});

describe('StreakReminderNudge', () => {
  it('renders for a native user with a streak and no prior decision', () => {
    render(<StreakReminderNudge />);
    expect(screen.getByRole('button', { name: /enable/i })).toBeInTheDocument();
  });

  it('enabling requests permission, sets the flag, and syncs', async () => {
    render(<StreakReminderNudge />);
    fireEvent.click(screen.getByRole('button', { name: /enable/i }));
    await waitFor(() => expect(requestPerm).toHaveBeenCalled());
    expect(localStorage.getItem(ENABLED_KEY)).toBe('1');
    expect(localStorage.getItem(NUDGE_KEY)).toBe('1');
    expect(sync).toHaveBeenCalled();
  });

  it('dismiss sets the seen flag and hides without enabling', () => {
    render(<StreakReminderNudge />);
    fireEvent.click(screen.getByRole('button', { name: /not now/i }));
    expect(localStorage.getItem(NUDGE_KEY)).toBe('1');
    expect(localStorage.getItem(ENABLED_KEY)).toBeNull();
  });

  it('renders nothing on web', () => {
    isNative.mockReturnValue(false);
    const { container } = render(<StreakReminderNudge />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing once already seen', () => {
    localStorage.setItem(NUDGE_KEY, '1');
    const { container } = render(<StreakReminderNudge />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd frontend && npx vitest run src/components/child/__tests__/StreakReminderNudge.test.tsx` → FAIL (component missing).

- [ ] **Step 3: Implement the component** — `frontend/src/components/child/StreakReminderNudge.tsx`:

```tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { isNativeApp } from '@/lib/platform';
import { REMINDER } from '@/lib/reminderConfig';
import { requestReminderPermission, syncStreakReminder } from '@/lib/streakReminder';
import { useProgress } from '@/hooks/useProgress';

const NUDGE_SEEN_KEY = 'notif_streak_nudge_seen';

/** One-time native nudge to enable the daily streak reminder. Shown to a child
 *  with a live streak who hasn't enabled it or dismissed the nudge. Web: null. */
export default function StreakReminderNudge() {
  const { t } = useTranslation('home');
  const { data: progress } = useProgress();
  const streakCount = progress?.streak_count ?? 0;
  const lastActivity = progress?.last_activity_date ?? null;

  const alreadyEnabled = localStorage.getItem(REMINDER.storageKey) === '1';
  const alreadySeen = localStorage.getItem(NUDGE_SEEN_KEY) === '1';
  const [dismissed, setDismissed] = useState(false);

  if (!isNativeApp() || streakCount <= 0 || alreadyEnabled || alreadySeen || dismissed) {
    return null;
  }

  function dismiss() {
    localStorage.setItem(NUDGE_SEEN_KEY, '1');
    setDismissed(true);
  }

  async function enable() {
    localStorage.setItem(NUDGE_SEEN_KEY, '1');
    const granted = await requestReminderPermission();
    if (granted) {
      localStorage.setItem(REMINDER.storageKey, '1');
      await syncStreakReminder({ lastActivity, streakCount });
    }
    setDismissed(true);
  }

  return (
    <section
      aria-label={t('streakNudge.title')}
      className="mb-4 rounded-2xl border border-line bg-card px-4 py-3"
    >
      <p className="text-sm font-semibold text-ink">{t('streakNudge.title')}</p>
      <p className="mb-3 text-sm text-muted-foreground">{t('streakNudge.body')}</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => void enable()}
          className="min-h-[44px] rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {t('streakNudge.enable')}
        </button>
        <button
          type="button"
          onClick={dismiss}
          className="min-h-[44px] rounded-md border border-line px-4 py-2 text-sm text-ink hover:bg-brand-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {t('streakNudge.dismiss')}
        </button>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Wire into Home + add i18n** — in `frontend/src/pages/child/Home.tsx`, import `StreakReminderNudge` and render `<StreakReminderNudge />` near the top of the returned content (above the hero/StatsCard). Confirm the namespace `Home.tsx` uses via its `useTranslation('<ns>')` call; the component above assumes `home`. Add these keys to `frontend/src/locales/en/<that-namespace>.json` (use the real namespace — likely `home.json`):

```json
"streakNudge": {
  "title": "Never miss your streak",
  "body": "Get a friendly daily reminder so your streak keeps growing.",
  "enable": "Enable reminders",
  "dismiss": "Not now"
}
```

If `Home.tsx` uses a namespace other than `home`, change the `useTranslation('home')` in the component to match and put the keys in that namespace's file. Keep the `no-literal-string` rule happy (all visible text via `t()`).

- [ ] **Step 5: Run to verify it passes** — `cd frontend && npx vitest run src/components/child/__tests__/StreakReminderNudge.test.tsx` → PASS. Then `npx tsc -b && npm run lint && npx vitest run src/pages/child/__tests__` (existing Home tests, if any) → green.

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid && git add frontend/src/components/child/StreakReminderNudge.tsx frontend/src/pages/child/Home.tsx frontend/src/locales/en frontend/src/components/child/__tests__/StreakReminderNudge.test.tsx && git commit -m "feat(streak): one-time native nudge to enable the daily reminder

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Full verification + promote

- [ ] **Step 1: Backend** — `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_entitlements_freshness.py tests/test_subscription_reconcile.py -q` green; spot-run the broader billing/entitlement suite (`pytest tests/ -k "entitle or billing or webhook or subscription" -q`).
- [ ] **Step 2: Frontend** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build` → all green; `no-literal-string` clean.
- [ ] **Step 3: iOS sync** — `cd frontend && npm run build && npx cap sync ios` (Units 1 & 3 ship in the native bundle).
- [ ] **Step 4: Push + green CI** — `git push origin testing`; confirm all 5 CI jobs green.
- [ ] **Step 5: Promote** — **No migration → no snapshot question.** Merge `testing → staging → main` on green CI at each stage; manual `vercel deploy --prod --archive=tgz --yes` + alias `app.investikid.ai`; verify `/health` 200. Confirm the new `internal/subscriptions/reconcile` route returns `403/401` unauth (deployed) and that the GitHub Actions cron includes it.
- [ ] **Step 6: Update trackers** (standing rule) — move this work into "Live in prod" in `docs/MASTER-BACKLOG.md` and note it in `docs/superpowers/PROGRESS.md` / the roadmap.

---

## Self-Review

**Spec coverage:**
- Unit 1 (refresh-on-401, single-flight, retry-once, give-up→login, auth-path skip) → Task 1. ✓
- Unit 2 guard (`current_period_end > now`, null still entitles) → Task 2. ✓
- Unit 2 reconcile (re-pull provider, best-effort per row, recompute, cron endpoint + schedule) → Task 3. ✓
- Unit 3 nudge (native-only, streak>0, not-seen/not-enabled, accept→permission→enable+sync, dismiss→suppress, web null) → Task 4. ✓
- No migration; promote testing→staging→main; cap sync ios; reconcile cron via existing `CRON_SECRET` → Task 5. ✓

**Placeholder scan:** real code in every step. The two soft spots are flagged with explicit verify-before-run notes, not left vague: (a) the `User`/`Subscription` seed kwargs in Tasks 2–3 must match the real models; (b) the `home` i18n namespace in Task 4 must match `Home.tsx`'s actual `useTranslation` namespace. Both are concrete checks, not TBDs.

**Type/name consistency:** `refreshSession`/`mutatingHeaders`/`isAuthPath` defined and used in Task 1. `_row_entitles` (Task 2) and `_repull*`/`run` (Task 3) names match their tests. `recompute_household_premium` is the single recompute seam used by both the guard (Task 2) and the reconcile (Task 3). `REMINDER.storageKey` + `NUDGE_SEEN_KEY` (Task 4) match the nudge tests. The reconcile reuses the real provider helpers (`_fetch_status`, `_fetch_subscription`/`_map_status`/`_expiry_dt`, `stripe.Subscription.retrieve`) with a verify-names note.
