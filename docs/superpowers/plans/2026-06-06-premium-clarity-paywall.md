# Free vs Premium Clarity + Paywall (4B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make free-vs-premium obvious everywhere and replace bare 403s / weak toasts with one friendly, reusable paywall that lets a child notify their parent to unlock — with no payment/steering in the child app (Apple 3.1.1).

**Architecture:** A structured `premium_required` 403 shape + a child→parent `PremiumRequest` (capped email + parent-dashboard flag, auto-resolved on subscribe). Frontend gains a `PremiumBadge`, a reusable `PremiumPaywall` bottom-sheet, and a `usePremiumPaywall()` context that any gated surface opens. No `is_premium` gating logic changes.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 async · Alembic · Postgres · React 18 · Vite · TS · TanStack Query · Tailwind v4 · shadcn/ui (Radix `Sheet`) · Vitest + vitest-axe.

**Spec:** `docs/superpowers/specs/2026-06-06-premium-clarity-paywall-design.md`

**Conventions (every task):**
- Repo: `/Users/leeashmore/investikid`; work on branch `testing`. Backend venv: `/Users/leeashmore/Local Repo/.venv/bin/`.
- Backend cmds from `backend`: `…/.venv/bin/pytest`, `…/.venv/bin/ruff check .`, `…/.venv/bin/alembic`.
- Async tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session` fixtures. New models exported from `app/models/__init__.py`.
- Child auth in tests: register via `/auth/register` then the request runs as that child (cookie). Parent auth: the `_setup_parent` + parent magic-link callback pattern from `tests/test_billing.py` (`issue_one_time_token(..., purpose=PARENT_MAGIC_AUDIENCE, ...)` → `GET /parent/auth/callback?token=…`). CSRF: `_csrf_headers(client)`.
- Frontend cmds from `frontend`: `npm test`, `npx tsc -b`, `npm run lint`. Run FULL `npm test` after FE changes; new UI gets `vitest-axe`; WCAG 2.2 AA (status never colour-only).
- Commit after each task; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Do NOT touch `.env*`.

---

## File Structure

**Backend — create:** `app/services/premium_config.py` (benefits, cooldown, `premium_required_error()`), `app/models/premium_request.py` (`PremiumRequest`), `app/routers/premium.py` (`POST /premium/request`), `app/schemas/premium.py`, `alembic/versions/<rev>_premium_request.py`.
**Backend — modify:** `app/models/__init__.py`, `app/services/email.py` (premium_request template), `app/routers/content.py` + `app/routers/simulator.py` + `app/routers/ai.py` (structured 403), `app/services/webhook_service.py` (resolve), `app/routers/parent.py` + `app/schemas/parent.py` (`GET /premium-requests`), `app/main.py` (register premium router).
**Frontend — create:** `src/lib/premiumConfig.ts`, `src/api/premium.ts`, `src/components/child/PremiumBadge.tsx`, `src/components/child/PremiumPaywall.tsx`, `src/hooks/usePremiumPaywall.tsx`, `src/components/parent/PremiumRequestsCard.tsx`.
**Frontend — modify:** `src/api/client.ts` (`ApiError` code/context), `src/main.tsx` or the child shell (mount provider), `src/components/child/ui/ModuleTile.tsx`, `src/pages/child/Module.tsx`, `src/pages/child/Level.tsx`, `src/pages/child/Stock.tsx`, the coach entry + challenges + ticker surfaces, `src/pages/ParentDashboard.tsx`.

---

## Task 1: `premium_config.py` (benefits, cooldown, error helper)

**Files:** Create `app/services/premium_config.py`; Test `tests/test_premium_config.py`.

- [ ] **Step 1: Failing test**
```python
# tests/test_premium_config.py
from fastapi import HTTPException

from app.services.premium_config import (
    PREMIUM_BENEFITS,
    PREMIUM_REQUEST_COOLDOWN_HOURS,
    premium_required_error,
)


def test_benefits_nonempty_strings():
    assert PREMIUM_BENEFITS and all(isinstance(b, str) and b for b in PREMIUM_BENEFITS)


def test_cooldown_positive():
    assert PREMIUM_REQUEST_COOLDOWN_HOURS > 0


def test_premium_required_error_shape():
    err = premium_required_error("level", "Investing Basics")
    assert isinstance(err, HTTPException)
    assert err.status_code == 403
    assert err.detail == {
        "message": "Premium required",
        "code": "premium_required",
        "context": {"kind": "level", "label": "Investing Basics"},
    }
```

- [ ] **Step 2: Run — fail** `…/.venv/bin/pytest tests/test_premium_config.py -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Implement**
```python
# app/services/premium_config.py
"""Central, developer-tuned config for premium clarity/paywall (deploy to change).

No prices here (App Store 3.1.1 — the child app never shows price/checkout). Benefits copy is
mirrored on the frontend in src/lib/premiumConfig.ts; keep the two in sync.
"""
from fastapi import HTTPException, status

# Canonical "what Premium includes" — used by the parent email + (mirrored) the app.
PREMIUM_BENEFITS: tuple[str, ...] = (
    "Coach Penny — your AI money helper",
    "Premium lessons & advanced levels",
    "The full stock market in the simulator",
    "Bonus challenges & rewards",
)

# Don't email the same parent more than once per this window.
PREMIUM_REQUEST_COOLDOWN_HOURS: int = 24


def premium_required_error(kind: str, label: str) -> HTTPException:
    """403 with a structured body the frontend uses to open the paywall.

    FastAPI serialises this as {"detail": {...}}.
    """
    return HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail={
            "message": "Premium required",
            "code": "premium_required",
            "context": {"kind": kind, "label": label},
        },
    )
```

- [ ] **Step 4: Run — pass** `…/.venv/bin/pytest tests/test_premium_config.py -v && …/.venv/bin/ruff check app/services/premium_config.py tests/test_premium_config.py`.

- [ ] **Step 5: Commit**
```bash
git add app/services/premium_config.py tests/test_premium_config.py
git commit -m "feat(premium): premium config — benefits, cooldown, 403 helper"
```

---

## Task 2: `PremiumRequest` model + migration

**Files:** Create `app/models/premium_request.py`; Modify `app/models/__init__.py`; Create `alembic/versions/d2e3f4a5b6c7_premium_request.py`; Test `tests/test_premium_request_model.py`.

- [ ] **Step 1: Failing test**
```python
# tests/test_premium_request_model.py
import uuid
from datetime import UTC, datetime

import pytest

from app.models.premium_request import PremiumRequest
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_premium_request_persists(db_session):
    import datetime as dt
    user = User(username=f"c{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex[:8]}@x.test",
                password_hash="x", dob=dt.date(2015, 1, 1), country_code="GB",
                currency_code="GBP", parent_email="p@x.test")
    db_session.add(user)
    await db_session.flush()
    req = PremiumRequest(child_user_id=user.id, parent_email="p@x.test",
                         context_kind="level", context_label="Investing Basics")
    db_session.add(req)
    await db_session.flush()
    assert req.id is not None
    assert req.resolved_at is None
    assert isinstance(req.created_at, datetime)
```

- [ ] **Step 2: Run — fail** `…/.venv/bin/pytest tests/test_premium_request_model.py -v` → `ModuleNotFoundError`.

- [ ] **Step 3: Create model**
```python
# app/models/premium_request.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PremiumRequest(Base):
    __tablename__ = "premium_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    context_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    context_label: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 4: Export** — add to `app/models/__init__.py` (alpha order, after `parent_session`):
```python
from app.models.premium_request import PremiumRequest  # noqa: F401
```

- [ ] **Step 5: Migration** — verify head first: `…/.venv/bin/alembic heads` (expect single `c1d2e3f4a5b6`; set `down_revision` to the real head).
```python
# alembic/versions/d2e3f4a5b6c7_premium_request.py
"""premium_request table"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "premium_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("child_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_email", sa.String(320), nullable=False),
        sa.Column("context_kind", sa.String(20), nullable=False),
        sa.Column("context_label", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_premium_requests_child_user_id", "premium_requests", ["child_user_id"])
    op.create_index("ix_premium_requests_parent_email", "premium_requests", ["parent_email"])
    op.create_index("ix_premium_requests_created_at", "premium_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_premium_requests_created_at", table_name="premium_requests")
    op.drop_index("ix_premium_requests_parent_email", table_name="premium_requests")
    op.drop_index("ix_premium_requests_child_user_id", table_name="premium_requests")
    op.drop_table("premium_requests")
```

- [ ] **Step 6: Run — pass** `…/.venv/bin/pytest tests/test_premium_request_model.py -v && …/.venv/bin/ruff check .` (do NOT run `alembic upgrade` against the live DB — single-file test only; CI validates the migration).

- [ ] **Step 7: Commit**
```bash
git add app/models/premium_request.py app/models/__init__.py alembic/versions/d2e3f4a5b6c7_premium_request.py tests/test_premium_request_model.py
git commit -m "feat(premium): PremiumRequest model + migration"
```

---

## Task 3: Email `premium_request` template

**Files:** Modify `app/services/email.py`; Test `tests/test_premium_email.py`.

- [ ] **Step 1: Read `app/services/email.py`** — note `_render()` (text branches), `_SUBJECT` dict, `_render_html()`. You'll add a `"premium_request"` branch to each, matching the existing style.

- [ ] **Step 2: Failing test**
```python
# tests/test_premium_email.py
import pytest
from sqlalchemy import select

from app.models.consent import SentEmail
from app.services.email import LoggingEmailSender

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_premium_request_email_renders_and_logs(db_session):
    await LoggingEmailSender().send(
        db_session, "parent@x.test", "premium_request",
        {"child_username": "ava", "context_label": "Investing Basics",
         "benefits": ["Coach Penny", "Premium lessons"]},
    )
    row = (await db_session.execute(
        select(SentEmail).where(SentEmail.template == "premium_request")
    )).scalars().first()
    assert row is not None
    assert "ava" in row.body
    assert "Investing Basics" in row.body
    assert "Coach Penny" in row.body
```

- [ ] **Step 3: Run — fail** `…/.venv/bin/pytest tests/test_premium_email.py -v` → `ValueError: Unknown template: premium_request`.

- [ ] **Step 4: Implement** — in `_render()` add a branch (match the neutral, no-price, no-external-link tone):
```python
    if template == "premium_request":
        child = context["child_username"]
        label = context["context_label"]
        benefits = "\n".join(f"- {b}" for b in context.get("benefits", []))
        return (
            f"Hi! {child} just discovered something in InvestiKid that needs Premium "
            f"(\"{label}\").\n\nPremium includes:\n{benefits}\n\n"
            "Open InvestiKid and head to your parent dashboard to manage your family's plan.\n"
        )
```
Add to `_SUBJECT`:
```python
    "premium_request": "Your child would love InvestiKid Premium",
```
Add a `"premium_request"` branch in `_render_html()` mirroring the structure of a neighbouring template (heading + body + a CTA that points to the **app/parent dashboard**, NOT an external checkout URL — use the app base URL `/parent` route, not a Stripe link).

- [ ] **Step 5: Run — pass** `…/.venv/bin/pytest tests/test_premium_email.py -v && …/.venv/bin/ruff check app/services/email.py`.

- [ ] **Step 6: Commit**
```bash
git add app/services/email.py tests/test_premium_email.py
git commit -m "feat(premium): premium_request email template (no external-purchase steering)"
```

---

## Task 4: `POST /premium/request` (child → parent)

**Files:** Create `app/routers/premium.py`, `app/schemas/premium.py`; Modify `app/main.py`; Test `tests/test_premium_request_endpoint.py`.

- [ ] **Step 1: Failing test** (mirror the child register flow)
```python
# tests/test_premium_request_endpoint.py
import pytest
from sqlalchemy import func, select

from app.models.consent import SentEmail
from app.models.premium_request import PremiumRequest

pytestmark = pytest.mark.asyncio(loop_scope="session")

REG = {"password": "SecurePass123!", "dob": "2010-05-10", "country_code": "GB",
       "currency_code": "GBP", "parent_email": "pr-parent@x.test"}


async def _login_child(client, email="pr-child@x.test", username="prchild"):
    await client.post("/auth/register", json={**REG, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_request_sends_email_then_caps(client, db_session):
    await _login_child(client)
    r1 = await client.post("/premium/request", json={"kind": "level", "label": "Investing Basics"})
    assert r1.status_code == 200 and r1.json()["status"] == "sent"
    r2 = await client.post("/premium/request", json={"kind": "level", "label": "Investing Basics"})
    assert r2.json()["status"] == "already_sent"
    emails = await db_session.scalar(
        select(func.count(SentEmail.id)).where(SentEmail.template == "premium_request"))
    assert emails == 1  # capped — only one email
    reqs = await db_session.scalar(
        select(func.count(PremiumRequest.id)).where(PremiumRequest.parent_email == "pr-parent@x.test"))
    assert reqs == 2  # both interest rows recorded
```
> Confirm the child registered with DOB age ≥ 14 is active and can log in (COPPA: under-13 GB pending-consent can't log in — DOB 2010 → age ~16, fine).

- [ ] **Step 2: Run — fail** → 404 (route missing).

- [ ] **Step 3: Schema** `app/schemas/premium.py`
```python
from pydantic import BaseModel, Field


class PremiumRequestIn(BaseModel):
    kind: str = Field(min_length=1, max_length=20)
    label: str = Field(min_length=1, max_length=200)


class PremiumRequestResult(BaseModel):
    status: str  # "sent" | "already_sent" | "no_parent"
```

- [ ] **Step 4: Router** `app/routers/premium.py`
```python
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.consent import SentEmail
from app.models.premium_request import PremiumRequest
from app.models.user import User
from app.routers.users import get_current_user
from app.schemas.premium import PremiumRequestIn, PremiumRequestResult
from app.services.email import get_email_sender
from app.services.premium_config import PREMIUM_BENEFITS, PREMIUM_REQUEST_COOLDOWN_HOURS

router = APIRouter(prefix="/premium", tags=["premium"])


@router.post("/request", response_model=PremiumRequestResult)
async def request_premium(
    payload: PremiumRequestIn,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    parent_email = current_user.parent_email
    if not parent_email:
        return PremiumRequestResult(status="no_parent")

    session.add(PremiumRequest(
        child_user_id=current_user.id, parent_email=parent_email,
        context_kind=payload.kind, context_label=payload.label,
    ))

    cutoff = datetime.now(UTC) - timedelta(hours=PREMIUM_REQUEST_COOLDOWN_HOURS)
    recent = await session.scalar(
        select(SentEmail.id).where(
            SentEmail.to_email == parent_email,
            SentEmail.template == "premium_request",
            SentEmail.sent_at > cutoff,
        ).limit(1)
    )
    if recent is not None:
        await session.commit()
        return PremiumRequestResult(status="already_sent")

    await get_email_sender().send(
        session, parent_email, "premium_request",
        {"child_username": current_user.username, "context_label": payload.label,
         "benefits": list(PREMIUM_BENEFITS)},
        subject_id=current_user.id,
    )
    await session.commit()
    return PremiumRequestResult(status="sent")
```
> Confirm `SentEmail` has a `sent_at` column (it does). Confirm `get_email_sender`/`SentEmail` import paths against `app/services/email.py` / `app/models/consent.py`.

- [ ] **Step 5: Register** — in `app/main.py`, import `from app.routers import premium as premium_router` and `application.include_router(premium_router.router)` (near the other child routers, before `billing_router`).

- [ ] **Step 6: Run — pass** `…/.venv/bin/pytest tests/test_premium_request_endpoint.py -v` and `…/.venv/bin/python -c "import app.main"` and ruff.

- [ ] **Step 7: Commit**
```bash
git add app/routers/premium.py app/schemas/premium.py app/main.py tests/test_premium_request_endpoint.py
git commit -m "feat(premium): POST /premium/request — capped child->parent email"
```

---

## Task 5: `GET /parent/premium-requests`

**Files:** Modify `app/routers/parent.py`, `app/schemas/parent.py`; Test `tests/test_parent_premium_requests.py`.

- [ ] **Step 1: Failing test** (parent auth via the billing test pattern)
```python
# tests/test_parent_premium_requests.py
from datetime import timedelta

import pytest

from app.models.premium_request import PremiumRequest
from app.models.user import User
from app.services.tokens import PARENT_MAGIC_AUDIENCE, issue_one_time_token
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _setup_parent(client, db_session, parent_email, child_email, child_username):
    await client.post("/auth/register", json={
        "email": child_email, "username": child_username, "password": "SecurePass123!",
        "dob": "2010-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": parent_email})
    token = await issue_one_time_token(db_session, purpose=PARENT_MAGIC_AUDIENCE,
                                       email=parent_email, subject_id=None,
                                       expires_in=timedelta(minutes=15))
    await db_session.commit()
    await client.get(f"/parent/auth/callback?token={token}")


async def test_lists_unresolved_for_this_parent_only(client, db_session):
    await _setup_parent(client, db_session, "ppr@x.test", "pprk@x.test", "pprk")
    child = await db_session.scalar(select(User).where(User.email == "pprk@x.test"))
    db_session.add(PremiumRequest(child_user_id=child.id, parent_email="ppr@x.test",
                                  context_kind="level", context_label="Investing Basics"))
    # a resolved one (should be excluded) + another parent's (must not leak)
    from datetime import UTC, datetime
    db_session.add(PremiumRequest(child_user_id=child.id, parent_email="ppr@x.test",
                                  context_kind="module", context_label="Taxes",
                                  resolved_at=datetime.now(UTC)))
    db_session.add(PremiumRequest(child_user_id=child.id, parent_email="other@x.test",
                                  context_kind="level", context_label="Other"))
    await db_session.commit()
    resp = await client.get("/parent/premium-requests")
    assert resp.status_code == 200
    data = resp.json()
    labels = [d["context_label"] for d in data]
    assert "Investing Basics" in labels
    assert "Taxes" not in labels and "Other" not in labels
    assert data[0]["child_username"] == "pprk"
```
> Confirm `issue_one_time_token` + `PARENT_MAGIC_AUDIENCE` import path from `tests/test_billing.py`.

- [ ] **Step 2: Run — fail** → 404.

- [ ] **Step 3: Schema** — add to `app/schemas/parent.py`:
```python
import uuid
from datetime import datetime


class PremiumRequestOut(BaseModel):
    id: uuid.UUID
    child_username: str
    context_kind: str
    context_label: str
    created_at: datetime
```
(Ensure `BaseModel` import + `uuid`/`datetime` are present.)

- [ ] **Step 4: Endpoint** — add to `app/routers/parent.py` (import `PremiumRequest`, `PremiumRequestOut`):
```python
@router.get("/premium-requests", response_model=list[PremiumRequestOut])
async def list_premium_requests(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(PremiumRequest, User.username)
        .join(User, User.id == PremiumRequest.child_user_id)
        .where(PremiumRequest.parent_email == parent_email,
               PremiumRequest.resolved_at.is_(None))
        .order_by(PremiumRequest.created_at.desc())
    )).all()
    return [
        PremiumRequestOut(id=r.id, child_username=username, context_kind=r.context_kind,
                          context_label=r.context_label, created_at=r.created_at)
        for r, username in rows
    ]
```

- [ ] **Step 5: Run — pass** `…/.venv/bin/pytest tests/test_parent_premium_requests.py -v` + ruff + `import app.main`.

- [ ] **Step 6: Commit**
```bash
git add app/routers/parent.py app/schemas/parent.py tests/test_parent_premium_requests.py
git commit -m "feat(premium): GET /parent/premium-requests (parent-scoped, unresolved)"
```

---

## Task 6: Resolve open requests on subscribe (webhook)

**Files:** Modify `app/services/webhook_service.py`; Test `tests/test_premium_request_resolve.py`.

- [ ] **Step 1: Failing test**
```python
# tests/test_premium_request_resolve.py
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.premium_request import PremiumRequest
from app.services.webhook_service import resolve_premium_requests

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_resolve_marks_open_requests(db_session):
    pe = "resolve@x.test"
    db_session.add(PremiumRequest(child_user_id=uuid.uuid4(), parent_email=pe,
                                  context_kind="level", context_label="X"))
    already = PremiumRequest(child_user_id=uuid.uuid4(), parent_email=pe,
                             context_kind="module", context_label="Y",
                             resolved_at=datetime.now(UTC))
    db_session.add(already)
    await db_session.flush()
    await resolve_premium_requests(db_session, pe)
    rows = (await db_session.execute(
        select(PremiumRequest).where(PremiumRequest.parent_email == pe))).scalars().all()
    assert all(r.resolved_at is not None for r in rows)
```

- [ ] **Step 2: Run — fail** → `ImportError: resolve_premium_requests`.

- [ ] **Step 3: Implement** — add to `app/services/webhook_service.py`:
```python
async def resolve_premium_requests(session: AsyncSession, parent_email: str) -> None:
    """Mark this parent's open premium requests resolved (called when premium is granted)."""
    from datetime import UTC, datetime

    from sqlalchemy import update

    from app.models.premium_request import PremiumRequest

    await session.execute(
        update(PremiumRequest)
        .where(PremiumRequest.parent_email == parent_email,
               PremiumRequest.resolved_at.is_(None))
        .values(resolved_at=datetime.now(UTC))
    )
```
Then call it inside `handle_checkout_completed`, AFTER the `set_premium` loop and BEFORE `await session.commit()`:
```python
    await resolve_premium_requests(session, parent_email)
```

- [ ] **Step 4: Run — pass** `…/.venv/bin/pytest tests/test_premium_request_resolve.py -v` + ruff + `import app.main`.

- [ ] **Step 5: Commit**
```bash
git add app/services/webhook_service.py tests/test_premium_request_resolve.py
git commit -m "feat(premium): resolve open premium requests on subscribe"
```

---

## Task 7: Structured `premium_required` 403 on every gate

**Files:** Modify `app/routers/content.py`, `app/routers/simulator.py`, `app/routers/ai.py`; update any existing tests asserting the old string detail; Test `tests/test_premium_403_shape.py`.

- [ ] **Step 1: Failing test**
```python
# tests/test_premium_403_shape.py
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

REG = {"password": "SecurePass123!", "dob": "2010-05-10", "country_code": "GB",
       "currency_code": "GBP", "parent_email": "g403@x.test"}


async def _login(client, email="g403@x.test.child", username="g403child"):
    await client.post("/auth/register", json={**REG, "email": email, "username": username})
    await client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_premium_ticker_403_is_structured(client):
    await _login(client)
    # A non-free-tier ticker for a free user → structured premium_required.
    resp = await client.post("/portfolio/trades",
                             json={"ticker": "NVDA", "exchange": "NASDAQ", "type": "buy", "shares": "1"})
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "premium_required"
    assert detail["context"]["kind"] == "ticker"
```
> Pick a ticker the `StaticPriceProvider` (test) treats as **non-free-tier**. Read `tests/conftest.py`'s `StaticPriceProvider.is_free_tier` to choose a ticker that returns False; adjust the test ticker/exchange to guarantee the premium path. If all test tickers are free-tier, extend the static provider minimally so one is not (in-scope).

- [ ] **Step 2: Run — fail** (detail is currently the plain string).

- [ ] **Step 3: Implement** — replace the three string-detail raises with the helper:
  - `app/routers/content.py` `_get_accessible_module`: `raise premium_required_error("module", module.title)` (import `from app.services.premium_config import premium_required_error`). In `_get_accessible_level`: `raise premium_required_error("level", level.title)`.
  - `app/routers/simulator.py` `place_trade`: `raise premium_required_error("ticker", payload.ticker)`.
  - `app/routers/ai.py` `home_greeting`: `raise premium_required_error("coach", "Coach Penny")`.

- [ ] **Step 4: Update existing tests** — grep for the old strings and fix any assertions:
```bash
…/.venv/bin/python - <<'PY'
import subprocess
print(subprocess.run(["grep","-rn","requires premium\|Premium required\|not available on free tier","tests"],capture_output=True,text=True).stdout)
PY
```
For each hit asserting `resp.json()["detail"] == "<string>"`, change it to assert `resp.json()["detail"]["code"] == "premium_required"` (or `["detail"]["message"]` if they want the message). Keep intent.

- [ ] **Step 5: Run — pass** `…/.venv/bin/pytest tests/test_premium_403_shape.py tests/ -k "premium or content or simulator or home_greeting or ai" -q` (new + touched green) + ruff + `import app.main`.

- [ ] **Step 6: Commit**
```bash
git add app/routers/content.py app/routers/simulator.py app/routers/ai.py tests/
git commit -m "feat(premium): structured premium_required 403 on all gates"
```

---

## Task 8: Frontend `ApiError` carries `code` + `context`

**Files:** Modify `src/api/client.ts`; Test `tests/unit/client-premium.test.ts`.

- [ ] **Step 1: Failing test**
```typescript
// tests/unit/client-premium.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, ApiError } from '@/api/client';

describe('apiFetch premium error', () => {
  beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('exposes code + context from a structured detail', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({
      detail: { message: 'Premium required', code: 'premium_required',
                context: { kind: 'level', label: 'Investing Basics' } },
    }), { status: 403 }));
    try {
      await apiFetch('/levels/x/lessons');
      throw new Error('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(403);
      expect(err.code).toBe('premium_required');
      expect((err.context as any).kind).toBe('level');
      expect(err.detail).toBe('Premium required');
    }
  });

  it('still works with a plain string detail', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Nope' }), { status: 400 }));
    await expect(apiFetch('/x')).rejects.toMatchObject({ status: 400, detail: 'Nope' });
  });
});
```

- [ ] **Step 2: Run — fail** `npm test -- client-premium`.

- [ ] **Step 3: Implement** — in `src/api/client.ts`:
```typescript
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
```
And in `apiFetch`, replace the error-parsing block:
```typescript
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
```

- [ ] **Step 4: Run — pass** `npm test -- client-premium && npx tsc -b`.

- [ ] **Step 5: Commit**
```bash
git add src/api/client.ts tests/unit/client-premium.test.ts
git commit -m "feat(premium): ApiError carries code + context"
```

---

## Task 9: Frontend premium config + API client

**Files:** Create `src/lib/premiumConfig.ts`, `src/api/premium.ts`; Test `tests/unit/premium-api.test.ts`.

- [ ] **Step 1: Failing test**
```typescript
// tests/unit/premium-api.test.ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { premiumApi } from '@/api/premium';
import { PREMIUM_BENEFITS } from '@/lib/premiumConfig';

describe('premiumApi', () => {
  beforeEach(() => { document.cookie = 'csrf_token=t'; vi.spyOn(globalThis, 'fetch'); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('requestUnlock POSTs kind+label', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({ status: 'sent' }), { status: 200 }));
    const res = await premiumApi.requestUnlock({ kind: 'level', label: 'Investing Basics' });
    expect(res?.status).toBe('sent');
    const [path, init] = (globalThis.fetch as any).mock.calls[0];
    expect(path).toContain('/premium/request');
    expect(JSON.parse(init.body)).toEqual({ kind: 'level', label: 'Investing Basics' });
  });

  it('benefits are non-empty', () => { expect(PREMIUM_BENEFITS.length).toBeGreaterThan(0); });
});
```

- [ ] **Step 2: Run — fail** `npm test -- premium-api`.

- [ ] **Step 3: Implement**
```typescript
// src/lib/premiumConfig.ts — mirror of backend app/services/premium_config.py PREMIUM_BENEFITS
export const PREMIUM_BENEFITS: string[] = [
  'Coach Penny — your AI money helper',
  'Premium lessons & advanced levels',
  'The full stock market in the simulator',
  'Bonus challenges & rewards',
];
export const PAYWALL_TITLE = 'Premium unlocks more!';
export const PAYWALL_CTA = 'Ask my grown-up to unlock';
```
```typescript
// src/api/premium.ts
import { apiFetch } from './client';

export type PremiumRequestKind = 'module' | 'level' | 'challenge' | 'ticker' | 'coach';
export type PremiumRequestResult = { status: 'sent' | 'already_sent' | 'no_parent' };
export type ParentPremiumRequest = {
  id: string; child_username: string; context_kind: string;
  context_label: string; created_at: string;
};

export const premiumApi = {
  requestUnlock: (body: { kind: PremiumRequestKind; label: string }) =>
    apiFetch<PremiumRequestResult>('/premium/request', { method: 'POST', body: JSON.stringify(body) }),
  parentRequests: () => apiFetch<ParentPremiumRequest[]>('/parent/premium-requests'),
};
```

- [ ] **Step 4: Run — pass** `npm test -- premium-api && npx tsc -b`.

- [ ] **Step 5: Commit**
```bash
git add src/lib/premiumConfig.ts src/api/premium.ts tests/unit/premium-api.test.ts
git commit -m "feat(premium): frontend premium config + API client"
```

---

## Task 10: `PremiumBadge`

**Files:** Create `src/components/child/PremiumBadge.tsx`; Test `tests/unit/PremiumBadge.test.tsx` + `tests/a11y/premium-badge.a11y.test.tsx`.

- [ ] **Step 1: Failing tests**
```tsx
// tests/unit/PremiumBadge.test.tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PremiumBadge } from '@/components/child/PremiumBadge';

describe('PremiumBadge', () => {
  it('shows the word Premium + a glyph (not colour-only)', () => {
    render(<PremiumBadge />);
    expect(screen.getByText(/premium/i)).toBeInTheDocument();
    expect(screen.getByText('✨')).toBeInTheDocument();
  });
});
```
```tsx
// tests/a11y/premium-badge.a11y.test.tsx
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { PremiumBadge } from '@/components/child/PremiumBadge';

describe('a11y: PremiumBadge', () => {
  it('no axe violations', async () => {
    const { container } = render(<PremiumBadge />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run — fail** `npm test -- PremiumBadge premium-badge`.

- [ ] **Step 3: Implement**
```tsx
// src/components/child/PremiumBadge.tsx
export function PremiumBadge({ className }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-accent-100 px-2 py-0.5 text-xs font-semibold text-accent-700 ${className ?? ''}`}
    >
      <span aria-hidden="true">✨</span> Premium
    </span>
  );
}
```

- [ ] **Step 4: Run — pass** `npm test -- PremiumBadge premium-badge && npx tsc -b`.

- [ ] **Step 5: Commit**
```bash
git add src/components/child/PremiumBadge.tsx tests/unit/PremiumBadge.test.tsx tests/a11y/premium-badge.a11y.test.tsx
git commit -m "feat(premium): PremiumBadge component"
```

---

## Task 11: `PremiumPaywall` sheet + `usePremiumPaywall` provider

**Files:** Create `src/hooks/usePremiumPaywall.tsx`, `src/components/child/PremiumPaywall.tsx`; Test `tests/unit/PremiumPaywall.test.tsx` + `tests/a11y/premium-paywall.a11y.test.tsx`.

- [ ] **Step 1: Failing tests**
```tsx
// tests/unit/PremiumPaywall.test.tsx
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PremiumPaywallProvider, usePremiumPaywall } from '@/hooks/usePremiumPaywall';

function Trigger() {
  const { open } = usePremiumPaywall();
  return <button onClick={() => open({ kind: 'level', label: 'Investing Basics' })}>lock</button>;
}

describe('PremiumPaywall', () => {
  beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('opens with benefits and requests unlock', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({ status: 'sent' }), { status: 200 }));
    render(<PremiumPaywallProvider><Trigger /></PremiumPaywallProvider>);
    await userEvent.click(screen.getByText('lock'));
    expect(await screen.findByText(/premium unlocks/i)).toBeInTheDocument();
    expect(screen.getByText(/coach penny/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /ask my grown-up/i }));
    await waitFor(() => expect(screen.getByText(/let your grown-up know|told them/i)).toBeInTheDocument());
  });
});
```
```tsx
// tests/a11y/premium-paywall.a11y.test.tsx
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { PremiumPaywallProvider, usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { useEffect } from 'react';

function Open() {
  const { open } = usePremiumPaywall();
  useEffect(() => { open({ kind: 'coach', label: 'Coach Penny' }); }, [open]);
  return null;
}

describe('a11y: PremiumPaywall', () => {
  it('no axe violations when open', async () => {
    const { container } = render(<PremiumPaywallProvider><Open /></PremiumPaywallProvider>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run — fail** `npm test -- PremiumPaywall premium-paywall`.

- [ ] **Step 3: Implement provider + hook** `src/hooks/usePremiumPaywall.tsx`
```tsx
import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { PremiumPaywall } from '@/components/child/PremiumPaywall';
import type { PremiumRequestKind } from '@/api/premium';

export type PaywallContext = { kind: PremiumRequestKind; label: string; id?: string };
type Ctx = { open: (c: PaywallContext) => void };
const PaywallCtx = createContext<Ctx | null>(null);

export function PremiumPaywallProvider({ children }: { children: React.ReactNode }) {
  const [ctx, setCtx] = useState<PaywallContext | null>(null);
  const open = useCallback((c: PaywallContext) => setCtx(c), []);
  const value = useMemo(() => ({ open }), [open]);
  return (
    <PaywallCtx.Provider value={value}>
      {children}
      <PremiumPaywall context={ctx} onClose={() => setCtx(null)} />
    </PaywallCtx.Provider>
  );
}

export function usePremiumPaywall(): Ctx {
  const c = useContext(PaywallCtx);
  if (!c) throw new Error('usePremiumPaywall must be used within PremiumPaywallProvider');
  return c;
}
```
> Note: `useCallback` import is from `react` (fix the import to `import { createContext, useCallback, useContext, useMemo, useState } from 'react'`).

- [ ] **Step 4: Implement the sheet** `src/components/child/PremiumPaywall.tsx` (mirror `CoachPanel`)
```tsx
import { useState } from 'react';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Penny } from '@/components/child/ui/Penny';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { premiumApi } from '@/api/premium';
import { PAYWALL_CTA, PAYWALL_TITLE, PREMIUM_BENEFITS } from '@/lib/premiumConfig';
import type { PaywallContext } from '@/hooks/usePremiumPaywall';

export function PremiumPaywall({ context, onClose }: { context: PaywallContext | null; onClose: () => void }) {
  const isDesktop = useMediaQuery('(min-width: 640px)');
  const [sentStatus, setSentStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const open = context !== null;

  async function ask() {
    if (!context) return;
    setBusy(true);
    try {
      const res = await premiumApi.requestUnlock({ kind: context.kind, label: context.label });
      setSentStatus(res?.status ?? 'sent');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) { onClose(); setSentStatus(null); } }}>
      <SheetContent
        side={isDesktop ? 'right' : 'bottom'}
        className={isDesktop
          ? 'flex h-full w-full max-w-md flex-col gap-0 border-brand-100 bg-white p-0 sm:max-w-md'
          : 'flex max-h-[85svh] flex-col gap-0 rounded-t-2xl border-brand-100 bg-white p-0'}
      >
        <SheetHeader className="flex-row items-center gap-2 border-b border-brand-100 px-4 py-3 text-left">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
            <Penny size={28} mood="happy" />
          </span>
          <div>
            <SheetTitle>{PAYWALL_TITLE}</SheetTitle>
            <SheetDescription>
              {context ? `"${context.label}" is a Premium treat.` : 'Premium unlocks more.'}
            </SheetDescription>
          </div>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-auto px-4 py-3 pb-[calc(0.75rem+var(--safe-bottom))]">
          {sentStatus ? (
            <p className="py-6 text-center text-base font-semibold text-ink">
              {sentStatus === 'no_parent'
                ? 'Ask a grown-up to set up Premium for you. 💛'
                : sentStatus === 'already_sent'
                  ? "We already told your grown-up today 👍"
                  : "We've let your grown-up know! 🎉"}
            </p>
          ) : (
            <>
              <ul className="space-y-2">
                {PREMIUM_BENEFITS.map((b) => (
                  <li key={b} className="flex items-start gap-2 text-sm text-ink">
                    <span aria-hidden="true">✨</span><span>{b}</span>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={ask}
                disabled={busy}
                className="mt-4 w-full rounded-full bg-brand-gradient px-5 py-3 text-sm font-bold text-white shadow disabled:opacity-60"
              >
                {busy ? 'Sending…' : PAYWALL_CTA}
              </button>
              <button type="button" onClick={onClose} className="mt-2 w-full rounded-full px-5 py-2 text-sm font-semibold text-muted-foreground">
                Maybe later
              </button>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```
> No price, no external link (Apple 3.1.1). Confirm `Penny`, `useMediaQuery`, `Sheet*` import paths against `CoachPanel.tsx`.

- [ ] **Step 5: Run — pass** `npm test -- PremiumPaywall premium-paywall && npx tsc -b`.

- [ ] **Step 6: Commit**
```bash
git add src/hooks/usePremiumPaywall.tsx src/components/child/PremiumPaywall.tsx tests/unit/PremiumPaywall.test.tsx tests/a11y/premium-paywall.a11y.test.tsx
git commit -m "feat(premium): PremiumPaywall sheet + usePremiumPaywall provider"
```

---

## Task 12: Mount provider + wire module/level surfaces

**Files:** Modify the child shell/root (where child routes render — find via `src/main.tsx` / the child layout `Shell`), `src/components/child/ui/ModuleTile.tsx`, `src/pages/child/Module.tsx`, `src/pages/child/Level.tsx`; Test: extend `tests/unit/child-Module.test.tsx` (or create) for the level-locked path.

- [ ] **Step 1: Mount the provider** — wrap the child app tree (inside the QueryClientProvider, around the child routes) with `<PremiumPaywallProvider>`. Find the child shell/layout (the component rendering child routes, e.g. `src/components/child/Shell.tsx`) and wrap its children, OR wrap at `src/main.tsx` if all child routes share a root. Verify with `npx tsc -b` and that existing child page tests still mount (some may need the provider in their render harness — update those minimally).

- [ ] **Step 2: Failing test** (Module level-locked opens paywall)
```tsx
// in tests/unit/child-Module.test.tsx — add a case
it('tapping a premium-locked level opens the paywall', async () => {
  // render Module within PremiumPaywallProvider + QueryClient + MemoryRouter,
  // mock GET /modules/:id/levels to return a level with state:'locked', locked_reason:'premium'
  // click it; assert the paywall ("Premium unlocks") appears (not the old toast).
});
```
(Use the existing Module test harness; mock fetch routes as the suite does.)

- [ ] **Step 3: Wire `Module.tsx`** — replace the premium branch of `onLockedClick`:
```tsx
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
// inside component:
const { open: openPaywall } = usePremiumPaywall();
// in onLockedClick:
onLockedClick={() => {
  if (level.locked_reason === 'premium') {
    openPaywall({ kind: 'level', label: level.title });
  } else {
    toast({ title: 'Locked', description: 'Finish the previous level first.' });
  }
}}
```

- [ ] **Step 4: Wire `Level.tsx`** — replace the static 403 block: when `err instanceof ApiError && err.code === 'premium_required'`, open the paywall and render a minimal placeholder (the sheet carries the message):
```tsx
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { useEffect } from 'react';
// inside component (top-level hook):
const { open: openPaywall } = usePremiumPaywall();
const premiumErr = lessonsQ.isError && lessonsQ.error instanceof ApiError
  && lessonsQ.error.code === 'premium_required' ? lessonsQ.error : null;
useEffect(() => {
  if (premiumErr) {
    const ctx = (premiumErr.context as { label?: string }) ?? {};
    openPaywall({ kind: 'level', label: ctx.label ?? 'this level' });
  }
}, [premiumErr, openPaywall]);
// in the error render branch, replace the static premium text with a back button + a "Premium" line + a button that re-opens the paywall.
```

- [ ] **Step 5: Wire `ModuleTile.tsx`** — when `locked`, add the `PremiumBadge` and make the tile clickable to a passed `onLockedClick` (today a locked tile is an inert `<div>`). Add an optional `onLockedClick?: () => void` prop; render a `<button>` when `locked && onLockedClick`. In `Home.tsx`/`Lessons.tsx` (module grids), pass `onLockedClick={() => openPaywall({ kind: 'module', label: m.title })}` for premium-locked modules. (Keep progression/region locks as-is.)

- [ ] **Step 6: Run — pass** `npm test && npx tsc -b && npm run lint` (full suite; update any child-page test harness that now needs the provider).

- [ ] **Step 7: Commit**
```bash
git add src/main.tsx src/components/child/ src/pages/child/Module.tsx src/pages/child/Level.tsx src/components/child/ui/ModuleTile.tsx src/pages/child/Home.tsx src/pages/child/Lessons.tsx tests/
git commit -m "feat(premium): paywall on module/level locks"
```

---

## Task 13: Wire simulator ticker + AI coach + premium challenges

**Files:** Modify `src/pages/child/Stock.tsx` (trade 403), the coach entry component, the challenges list, and the ticker picker; Test: extend `tests/unit/child-Stock.test.tsx`.

- [ ] **Step 1: Failing test** (premium ticker 403 → paywall) — in `tests/unit/child-Stock.test.tsx`, mock `POST /portfolio/trades` to reject with a 403 whose body is `{ detail: { code: 'premium_required', context: { kind: 'ticker', label: 'NVDA' } } }`; submit a buy; assert the paywall opens (rendered within `PremiumPaywallProvider` in the harness).

- [ ] **Step 2: Wire `Stock.tsx`** — in the `placeTrade` mutation `onError`, detect the premium code and open the paywall (reuse the existing `onError`):
```tsx
import { ApiError } from '@/api/client';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
// inside component: const { open: openPaywall } = usePremiumPaywall();
// in onError(err):
if (err instanceof ApiError && err.code === 'premium_required') {
  const ctx = (err.context as { label?: string }) ?? {};
  openPaywall({ kind: 'ticker', label: ctx.label ?? 'this stock' });
  return; // skip the generic error toast
}
```

- [ ] **Step 3: Wire the AI coach entry** — find the coach FAB/entry that opens `CoachPanel` (search `src/components/child` for `CoachPanel` usage / a `Coach` FAB). For a non-premium child, the entry shows the `PremiumBadge` and tapping opens the paywall (`openPaywall({ kind: 'coach', label: 'Coach Penny' })`) instead of the panel. Gate on the child's `is_premium` (read via the existing `useMe`/me query the app already uses — find how `is_premium` is read elsewhere and reuse).

- [ ] **Step 4: Wire premium challenges** — find the challenges list component (search for `challenges`/`is_premium` in `src/components/child` or a Stats/Quests page). For each challenge with `is_premium`, render the `PremiumBadge`; if the child isn't premium, tapping opens `openPaywall({ kind: 'challenge', label: challenge.title })`.

- [ ] **Step 5: Wire premium tickers in the picker** — in the simulator market/search/picker, tag non-free-tier tickers with the `PremiumBadge` for non-premium children (cosmetic clarity; the trade 403 already routes to the paywall on attempt). Find the ticker list/search component under `src/components/child/simulator`.

> For Steps 3–5: these surfaces weren't fully mapped during planning. Locate each host component (named above), then apply the **established** integration: `PremiumBadge` for the marker + `usePremiumPaywall().open({ kind, label })` on tap, gated by the child's `is_premium`. If a surface genuinely can't be found, report it rather than inventing one.

- [ ] **Step 6: Run — pass** `npm test && npx tsc -b && npm run lint`.

- [ ] **Step 7: Commit**
```bash
git add src/pages/child/Stock.tsx src/components/child/ tests/
git commit -m "feat(premium): paywall on premium ticker, coach, and challenges"
```

---

## Task 14: Parent dashboard "Premium requested" indicator

**Files:** Create `src/components/parent/PremiumRequestsCard.tsx`; Modify `src/pages/ParentDashboard.tsx`; Test `tests/unit/PremiumRequestsCard.test.tsx` + `tests/a11y/premium-requests-card.a11y.test.tsx`.

- [ ] **Step 1: Failing tests**
```tsx
// tests/unit/PremiumRequestsCard.test.tsx
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PremiumRequestsCard } from '@/components/parent/PremiumRequestsCard';

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><PremiumRequestsCard /></QueryClientProvider>);
}

describe('PremiumRequestsCard', () => {
  beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('shows pending requests', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify([
      { id: 'r1', child_username: 'Ava', context_kind: 'level', context_label: 'Investing Basics', created_at: '2026-06-06T00:00:00Z' },
    ]), { status: 200 }));
    wrap();
    await waitFor(() => expect(screen.getByText(/Ava/)).toBeInTheDocument());
    expect(screen.getByText(/Investing Basics/)).toBeInTheDocument();
  });

  it('renders nothing when there are none', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response('[]', { status: 200 }));
    const { container } = wrap();
    await waitFor(() => expect(container.textContent).not.toMatch(/requested/i));
  });
});
```
```tsx
// tests/a11y/premium-requests-card.a11y.test.tsx — mock one request, assert axe clean (mirror an existing parent a11y test's setup)
```

- [ ] **Step 2: Run — fail** `npm test -- PremiumRequestsCard premium-requests-card`.

- [ ] **Step 3: Implement**
```tsx
// src/components/parent/PremiumRequestsCard.tsx
import { useQuery } from '@tanstack/react-query';
import { premiumApi } from '@/api/premium';

export function PremiumRequestsCard() {
  const q = useQuery({ queryKey: ['premium-requests'], queryFn: premiumApi.parentRequests, retry: false });
  const reqs = q.data ?? [];
  if (!reqs.length) return null;
  return (
    <section aria-label="Premium requests" className="mb-4 rounded-2xl border border-accent-200 bg-accent-50 p-4">
      <p className="text-sm font-bold text-accent-700">✨ Premium requested</p>
      <ul className="mt-1 space-y-0.5">
        {reqs.map((r) => (
          <li key={r.id} className="text-sm text-ink">
            <strong>{r.child_username}</strong> asked to unlock <em>{r.context_label}</em>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4: Slot into the dashboard** — in `src/pages/ParentDashboard.tsx`, render `<PremiumRequestsCard />` immediately above `<SubscriptionCard />`.

- [ ] **Step 5: Run — pass** `npm test && npx tsc -b && npm run lint`.

- [ ] **Step 6: Commit**
```bash
git add src/components/parent/PremiumRequestsCard.tsx src/pages/ParentDashboard.tsx tests/unit/PremiumRequestsCard.test.tsx tests/a11y/premium-requests-card.a11y.test.tsx
git commit -m "feat(premium): parent dashboard premium-requests indicator"
```

---

## Task 15: Full regression + close-out

- [ ] **Step 1: Backend** (from `backend`): `…/.venv/bin/ruff check .` ; `…/.venv/bin/pytest tests/ -k "premium or content or simulator or webhook or parent or ai or email"` (touched areas; full suite optional — DB-hang gotcha applies, rely on CI). Confirm single alembic head: `…/.venv/bin/alembic heads`.
- [ ] **Step 2: Frontend** (from `frontend`): `npx tsc -b && npm run lint && npm test && npm run build`.
- [ ] **Step 3: Final holistic review** — dispatch a reviewer over the whole 4B diff focused on: Apple 3.1.1 (no price/external-purchase steering anywhere in the child app or email), COPPA (only child username + content label emailed to on-file parent; cap enforced server-side; IDOR-safe parent endpoint), and that no `is_premium` gating changed.
- [ ] **Step 4: Finish** — `superpowers:finishing-a-development-branch`. Stay on `testing`; commits already landed there. (Promotion `testing → staging → main` is a separate user step; the prod migration follows the **backup-first** rule in `docs/deployment-environments.md`.)

---

## Self-Review

**Spec coverage:** Unified vocabulary → Tasks 10 (badge) + 11 (paywall) + 12/13 (wiring). Child→parent request → Tasks 2 (model), 3 (email), 4 (endpoint), 6 (resolve). Parent visibility → Tasks 5 + 14. Comprehensive scope → Tasks 12 (module/level) + 13 (ticker/coach/challenges). Standardized `premium_required` → Tasks 7 (backend) + 8 (ApiError). Centralized config → Tasks 1 + 9. Apple/COPPA → enforced in Tasks 3/4/11 + reviewed in 15. ✅

**Placeholder scan:** Tasks 12 (provider mount point), 13 (coach/challenge/ticker host components) carry "locate the named host component, then apply the established `PremiumBadge` + `usePremiumPaywall().open()`" — deliberate, because those hosts weren't fully mapped; full integration code is given, only the file is to be confirmed. Task 7 Step 1 says to pick a non-free-tier test ticker by reading `StaticPriceProvider`. No TBD/TODO.

**Type consistency:** `premium_required_error(kind, label)` → 403 `{message, code, context:{kind,label}}` ↔ `ApiError{code, context}` ↔ `usePremiumPaywall().open({kind, label, id?})` ↔ `premiumApi.requestUnlock({kind, label})` ↔ `POST /premium/request {kind, label}` — names align across backend + frontend. `PremiumRequest`/`PremiumRequestOut`/`ParentPremiumRequest` field names (`child_username`, `context_kind`, `context_label`, `created_at`) consistent across Tasks 5, 9, 14.
