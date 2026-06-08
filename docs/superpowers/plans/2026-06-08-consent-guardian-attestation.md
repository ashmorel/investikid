# Parent/Guardian 18+ Attestation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require a parent/guardian to confirm they are the child's parent/legal guardian and over 18 before approving a child's account; record the attestation timestamp.

**Architecture:** Add a nullable `guardian_attested_at` column to `users`; require `attest_guardian=true` on the `/consent/decide` approve path (validated before the one-time token is consumed); gate the Approve button in `ConsentVerify.tsx` behind a checkbox.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + pydantic v2 (backend); React 18 + Vite + TS + TanStack Query + vitest/vitest-axe (frontend).

**Conventions (MANDATORY):**
- Branch `testing`. Explicit `git add <paths>` only — never `git add -A`. Leave the unrelated modified `.gitignore` untouched.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Backend tools: pytest `/Users/leeashmore/Local Repo/.venv/bin/pytest`, ruff `/Users/leeashmore/Local Repo/.venv/bin/ruff`, alembic `/Users/leeashmore/Local Repo/.venv/bin/alembic` (run from `backend/`).
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + the `db_session`/`client` fixtures.

---

### Task 1: Migration + model column (`guardian_attested_at`)

**Files:**
- Create: `backend/alembic/versions/a5b6c7d8e9f0_add_guardian_attested_at.py`
- Modify: `backend/app/models/user.py`
- Test: `backend/tests/models/test_guardian_attested_at.py`

- [ ] **Step 1: Confirm the current head**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: `f4a5b6c7d8e9 (head)` (single head). If different, use that value as `down_revision` below.

- [ ] **Step 2: Write the failing test** `backend/tests/models/test_guardian_attested_at.py`

```python
import pytest

from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_guardian_attested_at_defaults_none_and_persists(db_session):
    from datetime import UTC, date, datetime

    user = User(
        username="kid_attest",
        password_hash="x",
        dob=date(2015, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="parent@example.com",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    assert user.guardian_attested_at is None

    now = datetime.now(UTC)
    user.guardian_attested_at = now
    await db_session.flush()
    fetched = await db_session.get(User, user.id)
    assert fetched.guardian_attested_at is not None
```

- [ ] **Step 3: Run it, expect FAIL**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/models/test_guardian_attested_at.py -v`
Expected: FAIL (`AttributeError: ... 'guardian_attested_at'` or mapper error).

- [ ] **Step 4: Add the column to the model** in `backend/app/models/user.py`, immediately after the `parent_consent_given_at` column:

```python
    guardian_attested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

(`datetime` and `DateTime` are already imported in this file — confirm; if `DateTime` is not imported, add `from sqlalchemy import DateTime` consistent with existing imports.)

- [ ] **Step 5: Create the migration** `backend/alembic/versions/a5b6c7d8e9f0_add_guardian_attested_at.py`

```python
"""add guardian_attested_at to users

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-06-08

"""
import sqlalchemy as sa
from alembic import op

revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("guardian_attested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "guardian_attested_at")
```

- [ ] **Step 6: Verify single head + test passes + ruff**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` → expect `a5b6c7d8e9f0 (head)` (single).
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/models/test_guardian_attested_at.py -v` → expect PASS.
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/models/user.py alembic/versions/a5b6c7d8e9f0_add_guardian_attested_at.py tests/models/test_guardian_attested_at.py` → expect clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/user.py backend/alembic/versions/a5b6c7d8e9f0_add_guardian_attested_at.py backend/tests/models/test_guardian_attested_at.py
git commit -m "feat(consent): add guardian_attested_at column to users

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Schema + endpoint (require attestation on approve)

**Files:**
- Modify: `backend/app/schemas/consent.py`
- Modify: `backend/app/routers/consent.py` (the `decide_consent` handler)
- Test: `backend/tests/routers/test_consent_attestation.py`

Context — the current handler (`app/routers/consent.py`) consumes the one-time token FIRST, then applies the decision:
```python
@router.post("/consent/decide", status_code=200)
async def decide_consent(token, payload: ConsentDecision, session=...):
    try:
        record = await consume_one_time_token(session, token, CONSENT_AUDIENCE)
    except ...:
        raise _gone(...)
    ...
    now = datetime.now(UTC)
    if payload.decision == "approve":
        user.parent_consent_given_at = now
        user.is_active = True
    else:
        user.consent_declined_at = now
        user.is_active = False
    await session.commit()
    return {"status": "ok", "decision": payload.decision}
```

- [ ] **Step 1: Write the failing tests** `backend/tests/routers/test_consent_attestation.py`

Reuse the consent-token helpers the existing consent tests use. Look at `backend/tests/routers/test_consent.py` (or wherever consent flow is tested) for: how a pending child + a consent token are created (likely registering an under-age child via the `client` and reading the issued token, or calling `issue_one_time_token` directly). Mirror that exact setup. The three tests:

```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_approve_without_attestation_rejected(client, db_session):
    # Arrange: create a pending (inactive) under-age child + a valid consent token.
    # (Use the same helper/pattern as the existing consent tests.)
    token = await _make_pending_child_and_token(client, db_session)

    resp = await client.post(
        f"/consent/decide?token={token}",
        json={"decision": "approve"},  # attest_guardian omitted -> defaults False
    )
    assert resp.status_code == 400
    assert "attestation" in resp.json()["detail"].lower()

    # Token must NOT be consumed: a correct retry still works.
    resp2 = await client.post(
        f"/consent/decide?token={token}",
        json={"decision": "approve", "attest_guardian": True},
    )
    assert resp2.status_code == 200


async def test_approve_with_attestation_sets_timestamps(client, db_session):
    token, user_id = await _make_pending_child_and_token(client, db_session, return_id=True)
    resp = await client.post(
        f"/consent/decide?token={token}",
        json={"decision": "approve", "attest_guardian": True},
    )
    assert resp.status_code == 200
    from app.models.user import User
    user = await db_session.get(User, user_id)
    await db_session.refresh(user)
    assert user.parent_consent_given_at is not None
    assert user.guardian_attested_at is not None
    assert user.is_active is True


async def test_decline_does_not_require_attestation(client, db_session):
    token, user_id = await _make_pending_child_and_token(client, db_session, return_id=True)
    resp = await client.post(
        f"/consent/decide?token={token}",
        json={"decision": "decline"},
    )
    assert resp.status_code == 200
    from app.models.user import User
    user = await db_session.get(User, user_id)
    await db_session.refresh(user)
    assert user.consent_declined_at is not None
    assert user.guardian_attested_at is None
    assert user.is_active is False
```

Implement `_make_pending_child_and_token(...)` in this test module using the SAME mechanism the existing consent tests use to obtain a consent token (e.g. register an under-13 child via `POST /register` with a `parent_email`, then pull the token from the issued consent email/`SentEmail` or from `issue_one_time_token`). Read `backend/tests/routers/test_consent.py` first and copy its helper exactly rather than inventing a new path.

- [ ] **Step 2: Run tests, expect FAIL**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_consent_attestation.py -v`
Expected: FAIL (approve-without-attest currently returns 200; `attest_guardian` unknown field is ignored).

- [ ] **Step 3: Add `attest_guardian` to the schema** in `backend/app/schemas/consent.py`:

```python
class ConsentDecision(BaseModel):
    decision: Literal["approve", "decline"]
    attest_guardian: bool = False
```

- [ ] **Step 4: Update the endpoint** in `backend/app/routers/consent.py::decide_consent`. Add the guard at the very TOP of the function body, BEFORE `consume_one_time_token`, then set the new timestamp on approve:

```python
    if payload.decision == "approve" and payload.attest_guardian is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guardian attestation required",
        )
    try:
        record = await consume_one_time_token(session, token, CONSENT_AUDIENCE)
    except TokenInvalid:
        raise _gone("Link invalid or expired")
    # ... (unchanged token error handling) ...

    now = datetime.now(UTC)
    if payload.decision == "approve":
        user.parent_consent_given_at = now
        user.guardian_attested_at = now
        user.is_active = True
    else:
        user.consent_declined_at = now
        user.is_active = False
```

- [ ] **Step 5: Run tests, expect PASS + ruff**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_consent_attestation.py -v` → expect 3 PASS.
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/schemas/consent.py app/routers/consent.py tests/routers/test_consent_attestation.py` → expect clean.

- [ ] **Step 6: Run the existing consent tests to confirm no regression**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_consent.py -v` (adjust path to the actual existing consent test file). Expected: PASS. If an existing test does `approve` without `attest_guardian`, update it to pass `"attest_guardian": True` (that is a legitimate spec change, not a workaround).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/consent.py backend/app/routers/consent.py backend/tests/routers/test_consent_attestation.py
git commit -m "feat(consent): require guardian 18+ attestation on approve

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(If you had to update an existing consent test in Step 6, `git add` that file in this commit too.)

---

### Task 3: Frontend — API client + attestation checkbox

**Files:**
- Modify: `frontend/src/api/consent.ts`
- Modify: `frontend/src/pages/ConsentVerify.tsx`
- Test: `frontend/src/pages/__tests__/ConsentVerify.test.tsx` (create if absent; otherwise extend the existing test for this page)

- [ ] **Step 1: Update the API client** `frontend/src/api/consent.ts` — extend `decide` to send `attest_guardian`:

```typescript
  decide: (token: string, decision: Decision, attestGuardian = false) =>
    apiFetch<{ status: string; decision: Decision }>(
      `/consent/decide?token=${encodeURIComponent(token)}`,
      { method: 'POST', body: JSON.stringify({ decision, attest_guardian: attestGuardian }) },
    ),
```

- [ ] **Step 2: Write the failing test** `frontend/src/pages/__tests__/ConsentVerify.test.tsx`

Mock `@/api/consent` so `verify` resolves to a child summary and `decide` is a spy. Render `ConsentVerify` inside the app's test providers (QueryClientProvider + MemoryRouter with `?token=abc` — copy the provider/render setup from an existing page test, e.g. a sibling `__tests__` file). Tests:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';

// mock the api module
vi.mock('@/api/consent', () => ({
  consentApi: {
    verify: vi.fn(() => Promise.resolve({ username: 'sophie', age: 9, country_code: 'GB' })),
    decide: vi.fn(() => Promise.resolve({ status: 'ok', decision: 'approve' })),
  },
}));

// ... import consentApi (mocked), ConsentVerify, and a renderWithProviders helper ...

describe('ConsentVerify attestation', () => {
  beforeEach(() => vi.clearAllMocks());

  it('disables Approve until the guardian checkbox is checked, then sends attestGuardian=true', async () => {
    renderWithProviders('/consent/verify?token=abc');
    const approve = await screen.findByRole('button', { name: /approve/i });
    expect(approve).toBeDisabled();

    await userEvent.click(screen.getByRole('checkbox', { name: /parent or legal guardian/i }));
    expect(approve).toBeEnabled();

    await userEvent.click(approve);
    expect(consentApi.decide).toHaveBeenCalledWith('abc', 'approve', true);
  });

  it('allows Decline without the checkbox', async () => {
    renderWithProviders('/consent/verify?token=abc');
    const decline = await screen.findByRole('button', { name: /decline/i });
    expect(decline).toBeEnabled();
    await userEvent.click(decline);
    expect(consentApi.decide).toHaveBeenCalledWith('abc', 'decline');
  });

  it('has no axe violations on the decision screen', async () => {
    const { container } = renderWithProviders('/consent/verify?token=abc');
    await screen.findByRole('button', { name: /approve/i });
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

Note: the `decline` call passes no third arg → the client defaults `attestGuardian=false`. If you prefer an explicit assertion, assert `toHaveBeenCalledWith('abc', 'decline')`.

- [ ] **Step 3: Run it, expect FAIL**

Run: `cd frontend && npm run test -- ConsentVerify`
Expected: FAIL (no checkbox; Approve not disabled).

- [ ] **Step 4: Add the checkbox + gating** in `frontend/src/pages/ConsentVerify.tsx`. Add `const [attested, setAttested] = useState(false);` near the existing `done` state. In the decision block (the `return` with the Approve/Decline buttons), insert the checkbox above the button row and gate Approve:

```tsx
      <div className="mt-6 flex items-start gap-3">
        <input
          id="guardian-attest"
          type="checkbox"
          checked={attested}
          onChange={(e) => setAttested(e.target.checked)}
          className="mt-1 h-4 w-4"
        />
        <label htmlFor="guardian-attest" className="text-sm text-foreground">
          I confirm I am {child.username}'s parent or legal guardian and am over 18.
        </label>
      </div>
      <div className="mt-6 flex gap-3">
        <Button onClick={() => decide.mutate('approve')} disabled={!attested || decide.isPending}>
          Approve
        </Button>
        <Button variant="outline" onClick={() => decide.mutate('decline')} disabled={decide.isPending}>
          Decline
        </Button>
      </div>
```

Update the mutation so approve forwards the attestation. Change the `decide` mutation's `mutationFn` to pass the flag:

```tsx
  const decide = useMutation({
    mutationFn: (d: Decision) => consentApi.decide(token, d, d === 'approve' ? attested : false),
    onSuccess: (_data, d) => setDone(d),
  });
```

(Keep the rest of the file unchanged. The `h-4 w-4` checkbox is 16px; the label is the touch target via `htmlFor`.)

- [ ] **Step 5: Run tests, expect PASS**

Run: `cd frontend && npm run test -- ConsentVerify` → expect PASS (all 3).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/consent.ts frontend/src/pages/ConsentVerify.tsx frontend/src/pages/__tests__/ConsentVerify.test.tsx
git commit -m "feat(consent): guardian attestation checkbox gates Approve

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Full regression + close-out

**Files:** none (verification only)

- [ ] **Step 1: Backend lint + full test suite**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest -q`
Expected: ruff clean; tests pass. (If the local Postgres hangs ~90s+, note it as environmental and rely on CI — but the new consent/model tests should run.)

- [ ] **Step 2: Frontend full checks**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: all green.

- [ ] **Step 3: Push and confirm CI**

```bash
git push origin testing
```
Then confirm the CI run for the new HEAD is green (frontend, backend, security, a11y, responsive). No `cap sync` needed — this is a web/parent surface with no native-plugin change.

---

## Self-review notes
- Spec coverage: migration+column (Task 1), schema+endpoint+pre-token guard (Task 2), API client + checkbox + a11y (Task 3), regression (Task 4) — all spec sections covered.
- Type consistency: `attest_guardian` (snake, backend/JSON) ↔ `attestGuardian` (camel, TS arg); `guardian_attested_at` used identically in model, migration, and tests.
- Note for implementer: in Task 2 read the existing consent test file first and reuse its token-acquisition helper verbatim; do not invent a new token path.
