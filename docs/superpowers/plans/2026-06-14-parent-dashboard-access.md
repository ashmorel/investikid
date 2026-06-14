# Parent Dashboard Access & Discovery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing parent dashboard obvious and frictionless to reach (three doors), polish its empty/first-run state, and close the free-premium toggle leak — all on the email-only parent model.

**Architecture:** A parent session is minted only from proof of inbox control. We add two new proofs (a verified-email logged-in user; a consent approval) that mint the *same* existing `parent_session`, plus discoverability links. Premium on the parent surface becomes read-only (real subscription only); comps move to admin.

**Tech Stack:** FastAPI + SQLAlchemy async (backend), React 18 + TS + TanStack Query + vitest/vitest-axe (frontend). Spec: `docs/superpowers/specs/2026-06-14-parent-dashboard-access-design.md`.

**Working directory:** `/Users/leeashmore/investikid`. Backend cmds from `backend/` using `/Users/leeashmore/Local Repo/.venv/bin/pytest` and `…/ruff`. Frontend from `frontend/` using `npm run test`, `npx tsc -b`, `npm run lint`.

---

## File Structure

**Backend**
- `backend/app/schemas/user.py` — add `is_parent` to `UserProfile`.
- `backend/app/routers/users.py` — compute `is_parent` in `GET /users/me`.
- `backend/app/routers/parent_auth.py` — new `POST /parent/auth/from-session` bridge.
- `backend/app/routers/consent.py` — mint a parent session on consent approve.
- `backend/app/routers/parent.py` — remove `POST /children/{id}/premium`.
- `backend/app/routers/admin.py` — new admin `POST /admin/users/{id}/premium` for comps.
- `backend/app/services/digest_service.py` — add the dashboard URL to the digest context.
- Tests: `backend/tests/test_parent_access.py` (new, most backend tasks), plus edits to existing premium/consent tests if any assert the removed endpoint.

**Frontend**
- `frontend/src/api/auth.ts` — `Me.is_parent`; `authApi.parentFromSession()`.
- `frontend/src/api/parent.ts` — remove `setChildPremium`.
- `frontend/src/components/child/ProfileMenu.tsx` — "Parent area" entry when `me.is_parent`.
- `frontend/src/pages/ConsentVerify.tsx` — approve → redirect to `/parent`.
- `frontend/src/pages/Login.tsx` — "Are you a parent?" link.
- `frontend/src/components/ChildCard.tsx` — premium toggle → read-only status.
- `frontend/src/pages/ParentDashboard.tsx` — friendlier empty state + one-time welcome hint.
- Tests: co-located `__tests__` per the existing convention.

---

## Task 1: Backend — `is_parent` on `GET /users/me`

**Files:**
- Modify: `backend/app/schemas/user.py` (UserProfile, ~line 15-33)
- Modify: `backend/app/routers/users.py` (`get_profile`, ~line 45-47)
- Test: `backend/tests/test_parent_access.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_parent_access.py
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.user import User
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_parent_user(client, db_session, *, verified=True):
    """Register a normal user, optionally mark email verified, and link a child
    whose parent_email is this user's email. Returns the user's email."""
    suffix = uuid.uuid4().hex[:8]
    email = f"par{suffix}@example.com"
    await _register_and_login(client, email=email, username=f"par{suffix}")
    user = await db_session.scalar(select(User).where(User.email == email))
    user.email_verified_at = datetime.now(UTC) if verified else None
    # a child that lists this user as its parent
    child = User(
        username=f"kid{suffix}", email=None, password_hash="x", dob=None,
        country_code="GB", currency_code="GBP", parent_email=email, is_active=True,
    )
    db_session.add(child)
    await db_session.commit()
    return email


async def test_me_is_parent_true_for_verified_parent(client, db_session):
    await _make_parent_user(client, db_session, verified=True)
    r = await client.get("/users/me")
    assert r.status_code == 200
    assert r.json()["is_parent"] is True


async def test_me_is_parent_false_when_email_unverified(client, db_session):
    await _make_parent_user(client, db_session, verified=False)
    r = await client.get("/users/me")
    assert r.json()["is_parent"] is False


async def test_me_is_parent_false_for_non_parent(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"np{suffix}@example.com", username=f"np{suffix}")
    r = await client.get("/users/me")
    assert r.json()["is_parent"] is False
```

> NOTE: confirm the `User(...)` kwargs match `backend/app/models/user.py` (esp. nullable `dob`, `email`). If `dob` is non-nullable, pass `dob=datetime(2010,1,1).date()`.

- [ ] **Step 2: Run → fail**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_parent_access.py -q`
Expected: FAIL (`is_parent` not in response / KeyError).

- [ ] **Step 3: Add the schema field**

In `backend/app/schemas/user.py`, inside `class UserProfile`, next to `is_admin`:

```python
    is_admin: bool
    is_parent: bool = False  # verified email that is some child's parent_email
```

- [ ] **Step 4: Compute it in the endpoint**

In `backend/app/routers/users.py`, replace `get_profile`:

```python
from sqlalchemy import select  # ensure imported at top

async def _is_parent(session: AsyncSession, user: User) -> bool:
    if user.email_verified_at is None or not user.email:
        return False
    found = await session.scalar(
        select(User.id)
        .where(User.parent_email == user.email, User.deleted_at.is_(None))
        .limit(1)
    )
    return found is not None


@router.get("/me", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile = UserProfile.model_validate(current_user)
    profile.is_parent = await _is_parent(session, current_user)
    return profile
```

> Ensure `AsyncSession`, `get_session`, and `select` are imported in `users.py` (the `patch /me` handler already imports session/`AsyncSession`; add `select` if missing).

- [ ] **Step 5: Run → pass.** `pytest tests/test_parent_access.py -q` → 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/user.py backend/app/routers/users.py backend/tests/test_parent_access.py
git commit -m "feat(parent): expose is_parent on /me (verified-email bridge)"
```

---

## Task 2: Backend — `POST /parent/auth/from-session` bridge

**Files:**
- Modify: `backend/app/routers/parent_auth.py`
- Test: `backend/tests/test_parent_access.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from tests.test_billing import _csrf_headers


async def test_from_session_mints_parent_session(client, db_session):
    await _make_parent_user(client, db_session, verified=True)
    r = await client.post("/parent/auth/from-session", headers=_csrf_headers(client))
    assert r.status_code == 200
    # the minted parent_session now authorizes the dashboard
    assert (await client.get("/parent/children")).status_code == 200


async def test_from_session_403_when_unverified(client, db_session):
    await _make_parent_user(client, db_session, verified=False)
    r = await client.post("/parent/auth/from-session", headers=_csrf_headers(client))
    assert r.status_code == 403


async def test_from_session_403_for_non_parent(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"np{suffix}@example.com", username=f"np{suffix}")
    # mark verified so we isolate the "no child" branch
    from app.models.user import User as U
    u = await db_session.scalar(select(U).where(U.email == f"np{suffix}@example.com"))
    u.email_verified_at = datetime.now(UTC)
    await db_session.commit()
    r = await client.post("/parent/auth/from-session", headers=_csrf_headers(client))
    assert r.status_code == 403
```

- [ ] **Step 2: Run → fail.** `pytest tests/test_parent_access.py -k from_session -q` → 404 (route missing).

- [ ] **Step 3: Implement the endpoint**

In `backend/app/routers/parent_auth.py`, extend the existing `from app.routers.auth import …` line to also import `get_current_user`, and add (router prefix is already `/parent/auth`):

```python
from app.routers.auth import _cookie_samesite, _set_csrf_cookie, get_current_user  # extend existing import


@router.post("/from-session")
async def parent_from_session(
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Mint a parent_session for a logged-in user whose VERIFIED email is some
    child's parent_email — the no-extra-login bridge (Door 1)."""
    if current_user.email_verified_at is None or not current_user.email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "email_not_verified")
    has_child = await session.scalar(
        select(User.id).where(
            User.parent_email == current_user.email, User.deleted_at.is_(None)
        ).limit(1)
    )
    if has_child is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_a_parent")
    token = await issue_parent_session(session, current_user.email)
    await session.commit()
    secure = settings.environment != "development"
    response.set_cookie(
        _PARENT_COOKIE, token, max_age=7 * 86400, httponly=True,
        samesite=_cookie_samesite(), secure=secure, path="/",
    )
    _set_csrf_cookie(response, secure)
    return {"status": "ok"}
```

> `issue_parent_session`, `settings`, `select`, `User`, `_PARENT_COOKIE`, `status`, `Response` are already imported in this module (verify; add any missing).

- [ ] **Step 4: Run → pass.** `pytest tests/test_parent_access.py -k from_session -q` → 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/parent_auth.py backend/tests/test_parent_access.py
git commit -m "feat(parent): /parent/auth/from-session bridges a verified user session to a parent session"
```

---

## Task 3: Backend — consent approve mints a parent session

**Files:**
- Modify: `backend/app/routers/consent.py` (`decide_consent`)
- Test: `backend/tests/test_parent_access.py`

- [ ] **Step 1: Write the failing test** (append)

```python
from app.services.tokens import issue_one_time_token, CONSENT_AUDIENCE  # adjust to actual consent-token helper


async def test_consent_approve_sets_parent_session_cookie(client, db_session):
    # create an inactive child needing consent, with our email as parent
    suffix = uuid.uuid4().hex[:8]
    pemail = f"cap{suffix}@example.com"
    child = User(
        username=f"ckid{suffix}", email=None, password_hash="x", dob=None,
        country_code="GB", currency_code="GBP", parent_email=pemail, is_active=False,
    )
    db_session.add(child)
    await db_session.commit()
    token = await issue_one_time_token(db_session, subject_id=child.id, audience=CONSENT_AUDIENCE, email=pemail)
    await db_session.commit()

    client.cookies.clear()
    r = await client.post(f"/consent/decide?token={token}", json={"decision": "approve", "attest_guardian": True})
    assert r.status_code == 200
    assert "parent_session" in r.cookies
    # the cookie authorizes the dashboard for this parent_email
    assert (await client.get("/parent/children")).status_code == 200
```

> Adjust `issue_one_time_token`/`CONSENT_AUDIENCE` to the real helpers used by `auth.py`'s register flow (grep `CONSENT_AUDIENCE` and the token-issuing function). The point of the test: approve → `parent_session` cookie present → dashboard authorized.

- [ ] **Step 2: Run → fail.** Cookie `parent_session` absent.

- [ ] **Step 3: Implement**

In `backend/app/routers/consent.py`: add a `response: Response` parameter to `decide_consent`, and after the approve branch sets the child active, mint + set the cookie. Add imports at top:

```python
from fastapi import Response  # add to existing fastapi import
from app.core.config import settings
from app.routers.auth import _cookie_samesite, _set_csrf_cookie
from app.routers.parent_auth import _PARENT_COOKIE
from app.services.tokens import issue_parent_session
```

Change the handler signature and body:

```python
async def decide_consent(
    token: str,
    payload: ConsentDecision,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    ...  # (unchanged validation + token consume + user load)
    now = datetime.now(UTC)
    parent_token = None
    if payload.decision == "approve":
        user.parent_consent_given_at = now
        user.guardian_attested_at = now
        user.is_active = True
        if user.parent_email:
            parent_token = await issue_parent_session(session, user.parent_email)
    else:
        user.consent_declined_at = now
        user.is_active = False

    await session.commit()

    if parent_token:
        secure = settings.environment != "development"
        response.set_cookie(
            _PARENT_COOKIE, parent_token, max_age=7 * 86400, httponly=True,
            samesite=_cookie_samesite(), secure=secure, path="/",
        )
        _set_csrf_cookie(response, secure)
    return {"status": "ok", "decision": payload.decision}
```

> Importing `_PARENT_COOKIE` from `parent_auth` is fine (no cycle: `parent_auth` does not import `consent`). If a cycle appears, define `_PARENT_COOKIE = "parent_session"` locally.

- [ ] **Step 4: Run → pass.**

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/consent.py backend/tests/test_parent_access.py
git commit -m "feat(parent): consent approval mints a parent session (Door 2)"
```

---

## Task 4: Backend — close the free-premium leak

**Files:**
- Modify: `backend/app/routers/parent.py` (remove `set_child_premium`)
- Modify: `backend/app/routers/admin.py` (add admin comp endpoint)
- Test: `backend/tests/test_parent_access.py`; check `backend/tests/` for existing tests hitting `/parent/children/{id}/premium` and update them.

- [ ] **Step 1: Write the failing tests** (append)

```python
from tests.test_billing import _setup_parent  # existing parent+child fixture


async def test_parent_premium_endpoint_removed(client, db_session):
    parent = f"pp{uuid.uuid4().hex[:6]}@example.com"
    await _setup_parent(client, db_session, parent_email=parent,
                        child_email=f"ppk{uuid.uuid4().hex[:6]}@example.com",
                        child_username=f"ppk{uuid.uuid4().hex[:6]}")
    child = await db_session.scalar(select(User).where(User.parent_email == parent))
    r = await client.post(f"/parent/children/{child.id}/premium",
                          json={"premium": True}, headers=_csrf_headers(client))
    assert r.status_code in (404, 405)  # endpoint no longer exists on the parent surface
```

> Also: `grep -rn "children/.*premium\|setChildPremium" backend/tests` and delete/repoint any existing test that asserted the parent toggle granted premium (e.g. in `test_tier*`/`test_billing*`). The admin endpoint below replaces its coverage.

```python
async def test_admin_can_grant_premium(admin_client, db_session):
    # admin_client = a logged-in admin session fixture (see tests using /admin/*)
    u = User(username=f"ag{uuid.uuid4().hex[:6]}", email=None, password_hash="x",
             dob=None, country_code="GB", currency_code="GBP", is_active=True)
    db_session.add(u)
    await db_session.commit()
    r = await admin_client.post(f"/admin/users/{u.id}/premium",
                                json={"premium": True}, headers=_csrf_headers(admin_client))
    assert r.status_code == 200
    await db_session.refresh(u)
    assert u.is_premium is True
```

> Use whatever admin-session fixture the existing admin tests use (grep `admin_client` / `get_current_admin` in `tests/`). If none, build one mirroring an existing `/admin/*` test.

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3a: Remove the parent endpoint**

In `backend/app/routers/parent.py`, delete the entire `@router.post("/children/{user_id}/premium")` / `set_child_premium` block (~lines 233-245) and the now-unused `from app.services.entitlements import set_premium` import **only if** nothing else in `parent.py` uses it (grep first).

- [ ] **Step 3b: Add the admin comp endpoint**

In `backend/app/routers/admin.py` (uses `get_current_admin`), add:

```python
from app.services.entitlements import set_premium  # if not already imported


@router.post("/users/{user_id}/premium")
async def admin_set_user_premium(
    user_id: uuid.UUID,
    payload: PremiumToggleRequest,   # reuse the existing schema
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(get_current_admin),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    await set_premium(session, user, value=payload.premium, actor="admin")
    await session.commit()
    return {"status": "ok", "premium": payload.premium}
```

> Import `PremiumToggleRequest` (from `app.schemas.parent`) and `User`, `uuid`, `status` as needed. Confirm the admin router's auth dependency name (`get_current_admin`) and how its other handlers inject it.

- [ ] **Step 4: Run → pass.** Also run the broader suite touched: `pytest tests/test_parent_access.py tests/test_billing.py -q` (and any tier test you repointed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/parent.py backend/app/routers/admin.py backend/tests/
git commit -m "fix(billing): remove free parent premium toggle; comps move to admin endpoint"
```

---

## Task 5: Frontend — API types & methods

**Files:**
- Modify: `frontend/src/api/auth.ts` (Me type ~line 8-18; authApi ~line 43)
- Modify: `frontend/src/api/parent.ts` (remove `setChildPremium` ~line 120)
- Test: none (covered via component tests)

- [ ] **Step 1: Add `is_parent` to `Me`** in `frontend/src/api/auth.ts`:

```ts
  is_admin: boolean;
  is_parent?: boolean;   // verified email that is some child's parent_email
```

- [ ] **Step 2: Add the bridge call** to `authApi` in the same file:

```ts
  parentFromSession: () =>
    apiFetch<{ status: string }>('/parent/auth/from-session', { method: 'POST' }),
```

- [ ] **Step 3: Remove `setChildPremium`** from `frontend/src/api/parent.ts` (line ~120). (Its only caller, `ChildCard`, is rewritten in Task 9.)

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npx tsc -b`
Expected: PASS *after Task 9* removes the `setChildPremium` caller. If running standalone now, you may see a ChildCard error — that's fine; do Task 9 next. (Or do Step 3 as part of Task 9 to keep tsc green between tasks — recommended: move Step 3 into Task 9.)

- [ ] **Step 5: Commit** (Steps 1-2 only; commit Step 3 with Task 9)

```bash
git add frontend/src/api/auth.ts
git commit -m "feat(parent): Me.is_parent + authApi.parentFromSession"
```

---

## Task 6: Frontend — "Parent area" entry in the child menu (Door 1)

**Files:**
- Modify: `frontend/src/components/child/ProfileMenu.tsx`
- Test: `frontend/src/components/child/__tests__/ProfileMenu.parent.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

```tsx
// ProfileMenu.parent.test.tsx — mirror the setup in ProfileMenu.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

const navigate = vi.fn();
vi.mock('react-router-dom', async (orig) => ({ ...(await orig() as object), useNavigate: () => navigate }));
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: vi.fn() }));
const parentFromSession = vi.fn().mockResolvedValue({ status: 'ok' });
vi.mock('@/api/auth', () => ({ authApi: { logout: vi.fn(), updatePreferences: vi.fn(), parentFromSession }, TOPIC_OPTIONS: [] }));
vi.mock('@/api/content', () => ({ TOPIC_OPTIONS: [] }));
vi.mock('@/components/mobile/BottomSheet', () => ({ BottomSheet: () => null }));
vi.mock('@/components/child/FeedbackDialog', () => ({ FeedbackDialog: () => null }));
vi.mock('@/hooks/useMediaQuery', () => ({ useMediaQuery: () => true }));

import { useChildSession } from '@/hooks/useChildSession';
import { ProfileMenu } from '../ProfileMenu';
const mockSession = vi.mocked(useChildSession);

function wrap(ui: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient()}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>);
}

describe('ProfileMenu parent entry', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows Parent area when is_parent and navigates via the bridge', async () => {
    mockSession.mockReturnValue({ data: { id: '1', username: 'sam', is_admin: false, is_parent: true } } as ReturnType<typeof useChildSession>);
    wrap(<ProfileMenu username="sam" />);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    const item = await screen.findByRole('menuitem', { name: /parent area/i });
    await userEvent.click(item);
    expect(parentFromSession).toHaveBeenCalled();
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/parent'));
  });

  it('hides Parent area when not a parent', async () => {
    mockSession.mockReturnValue({ data: { id: '2', username: 'kid', is_admin: false, is_parent: false } } as ReturnType<typeof useChildSession>);
    wrap(<ProfileMenu username="kid" />);
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    expect(screen.queryByRole('menuitem', { name: /parent area/i })).toBeNull();
  });
});
```

- [ ] **Step 2: Run → fail.** `cd frontend && npx vitest run src/components/child/__tests__/ProfileMenu.parent.test.tsx`

- [ ] **Step 3: Implement**

In `ProfileMenu.tsx`, add a handler and a menu item (mirror the existing `Admin` menuitem that shows on `session?.is_admin`):

```tsx
import { authApi } from '@/api/auth';   // already imported

async function goToParentArea() {
  try { await authApi.parentFromSession(); } catch { /* dashboard guard will redirect if needed */ }
  navigate('/parent');
}
```

In the dropdown, next to the Admin item:

```tsx
{session?.is_parent && (
  <DropdownMenuItem onSelect={() => void goToParentArea()}>
    Parent area
  </DropdownMenuItem>
)}
```

- [ ] **Step 4: Run → pass.**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/child/ProfileMenu.tsx frontend/src/components/child/__tests__/ProfileMenu.parent.test.tsx
git commit -m "feat(parent): Parent area entry in the child menu (verified-email bridge)"
```

---

## Task 7: Frontend — consent approve redirects to the dashboard (Door 2)

**Files:**
- Modify: `frontend/src/pages/ConsentVerify.tsx` (~line 23-59)
- Test: `frontend/src/pages/__tests__/ConsentVerify.test.tsx` (create or extend)

- [ ] **Step 1: Write the failing test**

```tsx
const navigate = vi.fn();
vi.mock('react-router-dom', async (o) => ({ ...(await o() as object), useNavigate: () => navigate, useSearchParams: () => [new URLSearchParams('token=abc'), vi.fn()] }));
const decide = vi.fn().mockResolvedValue({ status: 'ok', decision: 'approve' });
vi.mock('@/api/consent', () => ({ consentApi: { verify: vi.fn().mockResolvedValue({ username: 'Yaz', age: 9, country_code: 'GB' }), decide } }));
// …render ConsentVerify, check the guardian box, click Approve…
// expect: navigate('/parent') called after a successful approve.
```

> Mirror the existing ConsentVerify render/flow. The behavioural assertion: after `decide('approve')` resolves, the component calls `navigate('/parent')` instead of only showing the static Success.

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement**

In `ConsentVerify.tsx`, add `const navigate = useNavigate();` and an `onSuccess` to the `decide` mutation that redirects on approve:

```tsx
const decide = useMutation({
  mutationFn: (d: Decision) => consentApi.decide(token, d, d === 'approve' ? attested : false),
  onSuccess: (_res, d) => { if (d === 'approve') navigate('/parent'); },
});
```

Keep the decline path as-is (it still shows the existing terminal message). The backend (Task 3) has already set the `parent_session` cookie, so `/parent` loads straight into the dashboard.

- [ ] **Step 4: Run → pass.**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ConsentVerify.tsx frontend/src/pages/__tests__/ConsentVerify.test.tsx
git commit -m "feat(parent): consent approval drops the parent into the dashboard"
```

---

## Task 8: Frontend — "Are you a parent?" link on the child login (Door 3)

**Files:**
- Modify: `frontend/src/pages/Login.tsx`
- Test: `frontend/src/pages/__tests__/Login.parent-link.test.tsx` (create) or extend an existing Login test

- [ ] **Step 1: Write the failing test**

```tsx
// render <Login/> inside MemoryRouter; assert a link to /parent/login exists
expect(screen.getByRole('link', { name: /parent/i })).toHaveAttribute('href', '/parent/login');
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement** — add near the existing "Create an account" / "Try a lesson" links in `Login.tsx`:

```tsx
<p className="text-sm text-muted-foreground">
  Are you a parent? <Link to="/parent/login" className="font-medium text-brand-700 underline">Manage your child</Link>
</p>
```

(Use the same `Link` import + styling already used by the other links on the page.)

- [ ] **Step 4: Run → pass.**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Login.tsx frontend/src/pages/__tests__/Login.parent-link.test.tsx
git commit -m "feat(parent): discoverable parent login link on the child sign-in screen"
```

---

## Task 9: Frontend — ChildCard premium toggle → read-only status (Door 5)

**Files:**
- Modify: `frontend/src/components/ChildCard.tsx` (~line 58-62 mutation; ~line 186-196 the premium `<Switch>` block)
- Modify: `frontend/src/api/parent.ts` (commit the Task 5 removal of `setChildPremium` here)
- Test: `frontend/src/components/__tests__/ChildCard.test.tsx` (update the premium tests)

- [ ] **Step 1: Update the failing tests**

In `ChildCard.test.tsx`, replace the three "premium toggle" tests (`renders an unchecked premium switch…`, `renders a checked premium switch…`, `grants premium when toggled on`) with read-only assertions:

```tsx
it('shows a Premium badge for a premium child (read-only, no switch)', () => {
  renderCard({ ...BASE_CHILD, is_premium: true });
  expect(screen.getByText(/Premium ✨/)).toBeInTheDocument();
  expect(screen.queryByRole('switch', { name: /premium/i })).toBeNull();
});

it('shows Free status for a non-premium child', () => {
  renderCard({ ...BASE_CHILD, is_premium: false });
  expect(screen.getByText(/Free plan/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run → fail.** `npx vitest run src/components/__tests__/ChildCard.test.tsx`

- [ ] **Step 3: Implement** — in `ChildCard.tsx`:
  - Delete the `premium` mutation (the `useMutation` calling `parentApi.setChildPremium`, ~line 58-62) and its import usage.
  - Replace the premium `<Switch>` block (~186-196) with a read-only status line:

```tsx
<div className="flex items-center gap-2 text-sm">
  {child.is_premium
    ? <span className="font-semibold text-brand-700">Premium ✨</span>
    : <span className="text-muted-foreground">Free plan</span>}
</div>
```

  - Apply the Task 5 Step 3 removal of `setChildPremium` from `api/parent.ts` now.

> Subscribing is unchanged — `<SubscriptionCard />` at the top of `ParentDashboard` (line 86) is the household-wide subscribe/manage surface.

- [ ] **Step 4: Run → pass.** `npx vitest run src/components/__tests__/ChildCard.test.tsx && npx tsc -b`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChildCard.tsx frontend/src/api/parent.ts frontend/src/components/__tests__/ChildCard.test.tsx
git commit -m "fix(billing): ChildCard shows read-only premium status; subscribe via SubscriptionCard only"
```

---

## Task 10: Frontend — friendlier empty state + first-visit hint (Door 4)

**Files:**
- Modify: `frontend/src/pages/ParentDashboard.tsx` (empty state ~line 98-101)
- Test: `frontend/src/pages/__tests__/ParentDashboard.empty.test.tsx` (create) or extend

- [ ] **Step 1: Write the failing test**

```tsx
// mock parentApi.listChildren → [] ; render ParentDashboard ; assert the guidance copy
expect(screen.getByText(/make sure your child entered/i)).toBeInTheDocument();
```

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement** — replace the empty-state block in `ParentDashboard.tsx`:

```tsx
{q.data && q.data.length === 0 && (
  <div className="rounded-xl border border-line bg-card p-4 text-sm text-muted-foreground">
    <p className="font-medium text-foreground">No children linked to this email yet.</p>
    <p className="mt-1">
      If your child has signed up, make sure they entered <strong>this exact email address</strong> as
      their parent's email when registering. Once they do, they'll appear here.
    </p>
  </div>
)}
```

Add a one-time welcome hint (dismissed via `localStorage`), rendered above the children list when there *are* children and the hint hasn't been dismissed:

```tsx
const [hintSeen, setHintSeen] = useState(() => localStorage.getItem('parent-welcome-seen') === '1');
// …in JSX, when q.data?.length:
{!hintSeen && (q.data?.length ?? 0) > 0 && (
  <div className="mb-4 flex items-start justify-between gap-3 rounded-xl border border-brand-200 bg-brand-50 p-3 text-sm">
    <span>Welcome! From here you can manage notifications, your subscription, Face ID sign-in, and your child's data.</span>
    <button type="button" className="font-semibold text-brand-700" onClick={() => { localStorage.setItem('parent-welcome-seen', '1'); setHintSeen(true); }}>Got it</button>
  </div>
)}
```

- [ ] **Step 4: Run → pass + axe.** `npx vitest run src/pages/__tests__/ParentDashboard.empty.test.tsx`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ParentDashboard.tsx frontend/src/pages/__tests__/ParentDashboard.empty.test.tsx
git commit -m "feat(parent): clearer empty state + one-time welcome hint on the dashboard"
```

---

## Task 11: Backend — weekly digest links to the dashboard (Door 3)

**Files:**
- Modify: the digest email template (find it) + `backend/app/services/digest_service.py` if the URL must be passed via context.
- Test: extend an existing digest test if one asserts rendered HTML, else a render assertion.

- [ ] **Step 1: Locate the template + base URL**

```bash
cd backend && grep -rn "digest" app/services/email.py app/templates 2>/dev/null
grep -rnE "frontend.*url|base_url|consent/verify|parent/auth/callback" app/core/config.py app/services/*.py | head
```

The consent + magic-link emails already build absolute frontend URLs from a settings value — reuse that exact setting (e.g. `settings.frontend_base_url`) to form `{base}/parent`.

- [ ] **Step 2: Write/extend the failing test**

Assert the rendered digest HTML contains a link to `…/parent` (mirror the existing email-render test pattern, e.g. `test_email.py::test_render_html_parent_magic_link`).

- [ ] **Step 3: Implement** — add a single line/button to the digest template:

```html
<p><a href="{{ parent_dashboard_url }}">Manage {{ child_name }} &amp; preferences →</a></p>
```

and pass `parent_dashboard_url = f"{settings.frontend_base_url.rstrip('/')}/parent"` into the digest context in `digest_service.py` (near the existing `"parent_email": parent_email` context, ~line 162).

- [ ] **Step 4: Run → pass.** `pytest tests/test_email.py tests/test_digest*.py -q`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/digest_service.py backend/app/templates backend/tests/
git commit -m "feat(parent): weekly digest links to the parent dashboard"
```

---

## Task 12: Full verification + push

- [ ] **Step 1: Backend gates**

```bash
cd backend
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app tests          # expect: All checks passed!
/Users/leeashmore/Local\ Repo/.venv/bin/pytest -q                     # expect: all pass (rely on CI if local PG hangs)
```

- [ ] **Step 2: Frontend gates**

```bash
cd frontend
npx tsc -b && echo TSC_OK
npm run lint                 # 0 errors
npx vitest run               # all pass, exit 0
npm run build                # success
```

- [ ] **Step 3: Manual sanity (the originating bug)** — note for the reviewer: with `yasmindreschashmore@icloud.com` listing `lee_ashmore@hotmail.co.uk` as `parent_email` and that user's email verified, logging in as `lee_ashmore` should now show **Parent area** → dashboard → Yasmin's card → Notifications toggle.

- [ ] **Step 4: Commit any stragglers, then push `testing`**

```bash
git push origin testing
```

Then confirm CI green and (standing rule) the Railway testing deploy SUCCESS + health 200. Do **not** promote — promotion is a separate, gated step (production migration? none here — this plan adds no migration, but still snapshot-ask before any prod DB change in future).

---

## Notes for the implementer
- **No DB migration** in this plan — `is_parent` is computed, not stored; no new columns.
- Every new session path reuses `issue_parent_session` + `_PARENT_COOKIE` + the 7-day revocable `ParentSession`. Do not invent a new session type.
- The security gate that must never regress: the logged-in bridge (`from-session`) and `is_parent` both require `email_verified_at is not None`. There is a test for the unverified-→ 403 / `is_parent=false` case; keep it.
- If `_register_and_login` / `_setup_parent` / `_csrf_headers` signatures differ from what's shown, adapt — they exist in `tests/test_content.py` and `tests/test_billing.py` respectively (grep to confirm exact kwargs).
