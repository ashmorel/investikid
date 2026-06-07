# Trial-Ending Reminder (Item 4C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Email each Stripe-trial parent once, ~2 days before their 7-day trial converts to paid, with a parent opt-out toggle in the dashboard, triggered by the existing daily cron.

**Architecture:** A new `parent_preferences` table holds the opt-out (parents have no table — keyed by `parent_email`). A pure-ish `trial_reminder_service.run(session)` selects in-window Stripe `trialing` subscriptions, dedupes via the `SentEmail` ledger (deterministic `uuid5` subject id), skips opt-outs, and sends a templated `trial_ending` email. A secret-guarded `/internal/trial-reminders/run` endpoint (mirroring video-health) is invoked as a second step in the existing daily GitHub Actions cron. Parents toggle the opt-out from the Parent Dashboard.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 async · Alembic · pydantic v2 · React 18 + Vite + TS + TanStack Query + Tailwind v4 + shadcn · pytest · vitest + vitest-axe.

**Conventions for every task:**
- Backend tools use the repo venv: `/Users/leeashmore/Local Repo/.venv/bin/pytest`, `/Users/leeashmore/Local Repo/.venv/bin/ruff`, `/Users/leeashmore/Local Repo/.venv/bin/alembic`. Run them from `/Users/leeashmore/investikid/backend`.
- Frontend commands run from `/Users/leeashmore/investikid/frontend`.
- Work on the `testing` branch. **Explicit `git add <paths>` only — never `git add -A`.** Leave the unrelated working-tree `.gitignore` change untouched.
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` and the `db_session` / `client` fixtures. For parent-authenticated endpoint tests, reuse the real magic-link parent-auth helper pattern from `backend/tests/routers/test_apple_billing.py` (its `_setup_parent`/parent-cookie pattern).

---

### Task 1: `parent_preferences` model + migration

**Files:**
- Create: `backend/app/models/parent_preferences.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/f4a5b6c7d8e9_add_parent_preferences.py`
- Test: `backend/tests/models/test_parent_preferences.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/models/test_parent_preferences.py`:
```python
import pytest

from app.models.parent_preferences import ParentPreferences

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_parent_preferences_defaults_opt_out_false(db_session):
    pref = ParentPreferences(parent_email="p@example.com")
    db_session.add(pref)
    await db_session.flush()

    fetched = await db_session.get(ParentPreferences, "p@example.com")
    assert fetched is not None
    assert fetched.trial_reminder_opt_out is False
    assert fetched.created_at is not None
    assert fetched.updated_at is not None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/models/test_parent_preferences.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.parent_preferences'`.

- [ ] **Step 3: Create the model**

Create `backend/app/models/parent_preferences.py` (timestamps mirror `app/models/subscription.py`):
```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ParentPreferences(Base):
    __tablename__ = "parent_preferences"

    parent_email: Mapped[str] = mapped_column(String(255), primary_key=True)
    trial_reminder_opt_out: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
```

- [ ] **Step 4: Register the model**

In `backend/app/models/__init__.py`, add (keep the list alphabetical-ish, after the `parent_identity` import):
```python
from app.models.parent_preferences import ParentPreferences  # noqa: F401
```

- [ ] **Step 5: Write the migration**

First confirm the head:
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: `e3f4a5b6c7d8 (head)`. If it differs, set `down_revision` to the actual single head.

Create `backend/alembic/versions/f4a5b6c7d8e9_add_parent_preferences.py`:
```python
"""add parent_preferences

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-06-07

"""
import sqlalchemy as sa
from alembic import op

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_preferences",
        sa.Column("parent_email", sa.String(length=255), nullable=False),
        sa.Column(
            "trial_reminder_opt_out",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("parent_email"),
    )


def downgrade() -> None:
    op.drop_table("parent_preferences")
```

- [ ] **Step 6: Verify migration chains + run the test**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/alembic heads`
Expected: `f4a5b6c7d8e9 (head)` (single head — no branch).
Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/models/test_parent_preferences.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**
```bash
git add backend/app/models/parent_preferences.py backend/app/models/__init__.py backend/alembic/versions/f4a5b6c7d8e9_add_parent_preferences.py backend/tests/models/test_parent_preferences.py
git commit -m "feat(4c): parent_preferences model + migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Config — `TRIAL_ENDING_REMINDER_DAYS`

**Files:**
- Modify: `backend/app/services/premium_config.py`

- [ ] **Step 1: Add the constant**

In `backend/app/services/premium_config.py`, directly below the existing `PREMIUM_REQUEST_COOLDOWN_HOURS` line, add:
```python
# Send the trial-ending reminder this many days before the trial converts to paid.
TRIAL_ENDING_REMINDER_DAYS: int = 2
```

- [ ] **Step 2: Verify import works**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/python -c "from app.services.premium_config import TRIAL_ENDING_REMINDER_DAYS; print(TRIAL_ENDING_REMINDER_DAYS)"`
Expected: `2`

- [ ] **Step 3: Commit**
```bash
git add backend/app/services/premium_config.py
git commit -m "feat(4c): TRIAL_ENDING_REMINDER_DAYS config

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `trial_ending` email template

**Files:**
- Modify: `backend/app/services/email.py`
- Test: `backend/tests/services/test_email_trial_ending.py`

Context keys the template consumes: `child_label` (str), `trial_end` (str), `benefits` (list[str]), `manage_hint` (str). No price/checkout link (App Store 3.1.1).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/services/test_email_trial_ending.py`:
```python
from app.services.email import _email_subject, _render, _render_html

CTX = {
    "child_label": "Sophie",
    "trial_end": "Friday 12 June",
    "benefits": ["Coach Penny", "Premium lessons"],
    "manage_hint": "Open InvestiKid to manage your plan.",
}


def test_trial_ending_subject():
    assert _email_subject("trial_ending") == "Your InvestiKid trial ends soon"


def test_trial_ending_text_has_child_date_benefits_no_price():
    body = _render("trial_ending", CTX)
    assert "Sophie" in body
    assert "Friday 12 June" in body
    assert "Coach Penny" in body
    assert "Open InvestiKid to manage your plan." in body
    assert "$" not in body and "£" not in body


def test_trial_ending_html_renders_benefits_and_cta():
    html = _render_html("trial_ending", CTX)
    assert "<!DOCTYPE html>" in html
    assert "Your InvestiKid trial ends soon" in html
    assert "<li" in html and "Premium lessons" in html
    assert "/parent" in html
```

- [ ] **Step 2: Run it to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_email_trial_ending.py -v`
Expected: FAIL — `_render` raises `ValueError: Unknown template: trial_ending`.

- [ ] **Step 3: Add the text branch**

In `backend/app/services/email.py`, inside `_render`, add this branch immediately before the final `raise ValueError(f"Unknown template: {template}")`:
```python
    if template == "trial_ending":
        child = context["child_label"]
        benefits = "\n".join(f"- {b}" for b in context.get("benefits", []))
        return (
            f"Hi!\n\n{child}'s InvestiKid free trial ends on {context['trial_end']}. "
            f"After that, Premium keeps unlocking:\n\n{benefits}\n\n"
            f"{context['manage_hint']}\n"
        )
```

- [ ] **Step 4: Add the subject**

In the `_SUBJECT` dict in `backend/app/services/email.py`, add the entry:
```python
    "trial_ending": "Your InvestiKid trial ends soon",
```

- [ ] **Step 5: Add the html branch**

In `_render_html`, add this branch immediately before the `else:` that raises `ValueError(f"Unknown template: {template}")` (it sets the shared `heading`/`body_text`/`cta_label`/`cta_url`/`footer` variables the shared tail renders):
```python
    elif template == "trial_ending":
        from app.core.config import settings

        child = context["child_label"]
        benefit_items = "".join(
            f"<li style=\"margin:0 0 6px;\">{b}</li>"
            for b in context.get("benefits", [])
        )
        heading = "Your InvestiKid trial ends soon"
        body_text = (
            f"{child}'s free trial ends on {context['trial_end']}. "
            f"After that, Premium keeps unlocking:"
            f"<ul style=\"margin:12px 0 0;padding-left:20px;\">{benefit_items}</ul>"
        )
        cta_label = "Open parent dashboard"
        cta_url = f"{settings.app_base_url}/parent"
        footer = context["manage_hint"]
```

- [ ] **Step 6: Run the test**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_email_trial_ending.py -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**
```bash
git add backend/app/services/email.py backend/tests/services/test_email_trial_ending.py
git commit -m "feat(4c): trial_ending email template

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `trial_reminder_service`

**Files:**
- Create: `backend/app/services/trial_reminder_service.py`
- Test: `backend/tests/services/test_trial_reminder_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/services/test_trial_reminder_service.py`:
```python
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.consent import SentEmail
from app.models.parent_preferences import ParentPreferences
from app.models.subscription import Subscription
from app.models.user import User
from app.services import trial_reminder_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _sub(parent_email, *, provider="stripe", status="trialing", days=1):
    return Subscription(
        parent_email=parent_email,
        provider=provider,
        external_id=f"ext-{uuid.uuid4()}",
        status=status,
        current_period_end=datetime.now(UTC) + timedelta(days=days),
    )


async def _count_emails(db_session, to_email):
    rows = (await db_session.scalars(
        select(SentEmail).where(SentEmail.to_email == to_email)
    )).all()
    return len(rows)


async def test_sends_for_in_window_stripe_trial(db_session):
    db_session.add(_sub("a@example.com", days=1))
    db_session.add(User(username="kid_a", password_hash="x", dob=date(2014, 1, 1),
                        country_code="GB", currency_code="GBP", parent_email="a@example.com"))
    await db_session.flush()

    result = await trial_reminder_service.run(db_session)

    assert result["sent"] == 1
    assert await _count_emails(db_session, "a@example.com") == 1


async def test_dedupes_on_second_run(db_session):
    db_session.add(_sub("b@example.com", days=1))
    await db_session.flush()

    first = await trial_reminder_service.run(db_session)
    second = await trial_reminder_service.run(db_session)

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert second["skipped"] == 1
    assert await _count_emails(db_session, "b@example.com") == 1


async def test_skips_opted_out_parent(db_session):
    db_session.add(_sub("c@example.com", days=1))
    db_session.add(ParentPreferences(parent_email="c@example.com", trial_reminder_opt_out=True))
    await db_session.flush()

    result = await trial_reminder_service.run(db_session)

    assert result["sent"] == 0
    assert result["skipped"] == 1
    assert await _count_emails(db_session, "c@example.com") == 0


async def test_ignores_non_stripe(db_session):
    db_session.add(_sub("d@example.com", provider="apple", days=1))
    await db_session.flush()
    result = await trial_reminder_service.run(db_session)
    assert result["sent"] == 0


async def test_ignores_non_trialing(db_session):
    db_session.add(_sub("e@example.com", status="active", days=1))
    await db_session.flush()
    result = await trial_reminder_service.run(db_session)
    assert result["sent"] == 0


async def test_ignores_out_of_window(db_session):
    db_session.add(_sub("f@example.com", days=10))   # too far out
    db_session.add(_sub("g@example.com", days=-1))   # already past
    await db_session.flush()
    result = await trial_reminder_service.run(db_session)
    assert result["sent"] == 0


async def test_child_label_fallback(db_session):
    db_session.add(_sub("h@example.com", days=1))  # no User rows for this parent
    await db_session.flush()
    result = await trial_reminder_service.run(db_session)
    assert result["sent"] == 1
    row = await db_session.scalar(
        select(SentEmail).where(SentEmail.to_email == "h@example.com")
    )
    assert "your child" in row.body
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_trial_reminder_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'trial_reminder_service'`.

- [ ] **Step 3: Implement the service**

Create `backend/app/services/trial_reminder_service.py`:
```python
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import SentEmail
from app.models.parent_preferences import ParentPreferences
from app.models.subscription import Subscription
from app.models.user import User
from app.services.email import get_email_sender
from app.services.premium_config import PREMIUM_BENEFITS, TRIAL_ENDING_REMINDER_DAYS

# Same namespace used for household_token (deterministic, stable across runs).
_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")
_MANAGE_HINT = "Open InvestiKid and go to your parent dashboard to manage your family's plan."


def _reminder_subject_id(subscription_id: uuid.UUID, period_end: datetime) -> uuid.UUID:
    """Deterministic id so re-runs dedupe against the SentEmail ledger."""
    return uuid.uuid5(_NAMESPACE, f"trial_ending:{subscription_id}:{period_end.date().isoformat()}")


async def run(session: AsyncSession) -> dict:
    now = datetime.now(UTC)
    cutoff = now + timedelta(days=TRIAL_ENDING_REMINDER_DAYS)

    subs = (await session.scalars(
        select(Subscription).where(
            Subscription.provider == "stripe",
            Subscription.status == "trialing",
            Subscription.current_period_end.is_not(None),
            Subscription.current_period_end > now,
            Subscription.current_period_end <= cutoff,
        )
    )).all()

    sender = get_email_sender()
    sent = 0
    skipped = 0
    for sub in subs:
        subject_id = _reminder_subject_id(sub.id, sub.current_period_end)

        already = await session.scalar(
            select(SentEmail.id).where(SentEmail.subject_id == subject_id).limit(1)
        )
        if already is not None:
            skipped += 1
            continue

        pref = await session.get(ParentPreferences, sub.parent_email)
        if pref is not None and pref.trial_reminder_opt_out:
            skipped += 1
            continue

        usernames = (await session.scalars(
            select(User.username).where(User.parent_email == sub.parent_email)
        )).all()
        child_label = ", ".join(usernames) if usernames else "your child"

        await sender.send(
            session,
            to=sub.parent_email,
            template="trial_ending",
            context={
                "child_label": child_label,
                "trial_end": sub.current_period_end.strftime("%A %-d %B"),
                "benefits": list(PREMIUM_BENEFITS),
                "manage_hint": _MANAGE_HINT,
            },
            subject_id=subject_id,
        )
        sent += 1

    await session.commit()
    return {"sent": sent, "skipped": skipped}
```

- [ ] **Step 4: Run the tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/services/test_trial_reminder_service.py -v`
Expected: PASS (7 tests). If `User(...)` construction fails on a required column, adjust the test helper to match the `User` model's required fields (see `app/models/user.py`) — keep `parent_email` set.

- [ ] **Step 5: Commit**
```bash
git add backend/app/services/trial_reminder_service.py backend/tests/services/test_trial_reminder_service.py
git commit -m "feat(4c): trial_reminder_service (Stripe-only, deduped, opt-out aware)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `/internal/trial-reminders/run` endpoint

**Files:**
- Modify: `backend/app/routers/internal.py`
- Test: `backend/tests/routers/test_internal_trial_reminders.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/routers/test_internal_trial_reminders.py`:
```python
import pytest

from app.core.config import settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_503_when_cron_secret_unset(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "", raising=False)
    resp = await client.post("/internal/trial-reminders/run")
    assert resp.status_code == 503


async def test_401_on_bad_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "right", raising=False)
    resp = await client.post("/internal/trial-reminders/run", headers={"X-Cron-Secret": "wrong"})
    assert resp.status_code == 401


async def test_200_with_summary(client, monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", "right", raising=False)
    resp = await client.post("/internal/trial-reminders/run", headers={"X-Cron-Secret": "right"})
    assert resp.status_code == 200
    body = resp.json()
    assert "sent" in body and "skipped" in body
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_internal_trial_reminders.py -v`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Add the endpoint**

In `backend/app/routers/internal.py`, add the import near the existing imports:
```python
from app.services import trial_reminder_service
```
Then add the route below `trigger_video_health`:
```python
@router.post("/trial-reminders/run")
async def trigger_trial_reminders(
    x_cron_secret: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not settings.cron_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if not x_cron_secret or not secrets.compare_digest(x_cron_secret, settings.cron_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return await trial_reminder_service.run(session)
```

- [ ] **Step 4: Run the tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_internal_trial_reminders.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
git add backend/app/routers/internal.py backend/tests/routers/test_internal_trial_reminders.py
git commit -m "feat(4c): /internal/trial-reminders/run cron endpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Wire the cron step (testing + main)

**Files:**
- Modify: `.github/workflows/video-health-cron.yml` (on `testing`, then the identical edit on `main` via worktree)

No automated test — verified by inspection + the existing manual cron validation.

- [ ] **Step 1: Add the second step on `testing`**

In `.github/workflows/video-health-cron.yml`, after the existing `Trigger video-health check` step (keep that step unchanged), append a sibling step inside the same `steps:` list:
```yaml
      - name: Trigger trial-ending reminders
        env:
          CRON_SECRET: ${{ secrets.CRON_SECRET }}
        run: |
          if [ -z "$CRON_SECRET" ]; then
            echo "::error::CRON_SECRET is empty. Add it under the Actions Secrets tab, matching the value set on the Railway backend."
            exit 1
          fi
          code=$(curl -sS -o /tmp/resp.txt -w "%{http_code}" -X POST \
            -H "X-Cron-Secret: $CRON_SECRET" \
            "$BACKEND_URL/internal/trial-reminders/run")
          echo "HTTP status: $code"
          cat /tmp/resp.txt; echo
          if [ "$code" != "200" ]; then
            echo "::error::Expected 200 but got $code. 401=secret mismatch with Railway; 503=CRON_SECRET unset on the backend; 404=endpoint not deployed."
            exit 1
          fi
```
Do **not** change the `env: BACKEND_URL: ${{ vars.BACKEND_URL || ... }}` block — it already resolves the target backend.

- [ ] **Step 2: Verify YAML is valid**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/video-health-cron.yml')); print('ok')"`
(run from `/Users/leeashmore/investikid`)
Expected: `ok`

- [ ] **Step 3: Commit on testing**
```bash
git add .github/workflows/video-health-cron.yml
git commit -m "ci(4c): add trial-reminders step to daily cron

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 4: Apply the identical edit to `main`**

The scheduled cron runs from the default branch (`main`), so the step must exist there too. Use an isolated worktree so the `testing` working tree is untouched:
```bash
cd /Users/leeashmore/investikid
git fetch origin main -q
git worktree add /tmp/ik-main-4c main
```
Apply the **same** `Trigger trial-ending reminders` step (Step 1's YAML) to `/tmp/ik-main-4c/.github/workflows/video-health-cron.yml`, then:
```bash
cd /tmp/ik-main-4c
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/video-health-cron.yml')); print('ok')"
git add .github/workflows/video-health-cron.yml
git commit -m "ci(4c): add trial-reminders step to daily cron

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin main
cd /Users/leeashmore/investikid
git worktree remove /tmp/ik-main-4c && git worktree prune
```
Note: this is a CI workflow file only — `main:false` on Vercel and manual Railway prod mean no deploy is triggered.

---

### Task 7: Parent preferences schemas + endpoints

**Files:**
- Create: `backend/app/schemas/parent_preferences.py`
- Modify: `backend/app/routers/parent.py`
- Test: `backend/tests/routers/test_parent_preferences.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/routers/test_parent_preferences.py` (reuse the magic-link parent-auth helper pattern from `tests/routers/test_apple_billing.py` — import or replicate its `_setup_parent` that returns an authenticated `client` for a `parent_email`):
```python
import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_get_preferences_requires_auth(client):
    resp = await client.get("/parent/preferences")
    assert resp.status_code in (401, 403)


async def test_get_defaults_false_then_patch_roundtrip(client, db_session):
    # Authenticate as a parent using the shared helper (see test_apple_billing.py).
    from tests.routers.test_apple_billing import _setup_parent
    await _setup_parent(client, db_session, "pref@example.com")

    got = await client.get("/parent/preferences")
    assert got.status_code == 200
    assert got.json() == {"trial_reminder_opt_out": False}

    patched = await client.patch(
        "/parent/preferences", json={"trial_reminder_opt_out": True}
    )
    assert patched.status_code == 200
    assert patched.json() == {"trial_reminder_opt_out": True}

    again = await client.get("/parent/preferences")
    assert again.json() == {"trial_reminder_opt_out": True}

    # Update existing row back to False
    off = await client.patch(
        "/parent/preferences", json={"trial_reminder_opt_out": False}
    )
    assert off.json() == {"trial_reminder_opt_out": False}
```
If `_setup_parent` is not importable from that module, replicate its body here (request magic link → consume callback → the `client` carries the parent session cookie).

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_parent_preferences.py -v`
Expected: FAIL — 404 on `/parent/preferences`.

- [ ] **Step 3: Add the schemas**

Create `backend/app/schemas/parent_preferences.py`:
```python
from pydantic import BaseModel


class ParentPreferencesOut(BaseModel):
    trial_reminder_opt_out: bool


class ParentPreferencesUpdate(BaseModel):
    trial_reminder_opt_out: bool
```

- [ ] **Step 4: Add the endpoints**

In `backend/app/routers/parent.py`, add imports:
```python
from app.models.parent_preferences import ParentPreferences
from app.schemas.parent_preferences import ParentPreferencesOut, ParentPreferencesUpdate
```
Then add the routes (anywhere among the other `@router` handlers):
```python
@router.get("/preferences", response_model=ParentPreferencesOut)
async def get_preferences(
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    pref = await session.get(ParentPreferences, parent_email)
    return ParentPreferencesOut(
        trial_reminder_opt_out=bool(pref and pref.trial_reminder_opt_out)
    )


@router.patch("/preferences", response_model=ParentPreferencesOut)
async def update_preferences(
    body: ParentPreferencesUpdate,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    pref = await session.get(ParentPreferences, parent_email)
    if pref is None:
        pref = ParentPreferences(
            parent_email=parent_email,
            trial_reminder_opt_out=body.trial_reminder_opt_out,
        )
        session.add(pref)
    else:
        pref.trial_reminder_opt_out = body.trial_reminder_opt_out
    await session.commit()
    return ParentPreferencesOut(trial_reminder_opt_out=body.trial_reminder_opt_out)
```

- [ ] **Step 5: Run the tests**

Run: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/routers/test_parent_preferences.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**
```bash
git add backend/app/schemas/parent_preferences.py backend/app/routers/parent.py backend/tests/routers/test_parent_preferences.py
git commit -m "feat(4c): parent preferences GET/PATCH endpoints

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Frontend API client

**Files:**
- Modify: `frontend/src/api/parent.ts`

- [ ] **Step 1: Add the type + methods**

In `frontend/src/api/parent.ts`, add an exported type near the other types:
```ts
export type ParentPreferences = { trial_reminder_opt_out: boolean };
```
Then inside the `parentApi` object, add:
```ts
  getPreferences: () => apiFetch<ParentPreferences>('/parent/preferences'),
  updatePreferences: (trialReminderOptOut: boolean) =>
    apiFetch<ParentPreferences>('/parent/preferences', {
      method: 'PATCH',
      body: JSON.stringify({ trial_reminder_opt_out: trialReminderOptOut }),
    }),
```

- [ ] **Step 2: Typecheck**

Run (from `frontend/`): `npx tsc -b`
Expected: no errors.

- [ ] **Step 3: Commit**
```bash
git add frontend/src/api/parent.ts
git commit -m "feat(4c): parent preferences API client

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: `NotificationPreferencesCard` + wire into ParentDashboard

**Files:**
- Create: `frontend/src/components/parent/NotificationPreferencesCard.tsx`
- Modify: `frontend/src/pages/ParentDashboard.tsx`
- Test: `frontend/src/components/parent/__tests__/NotificationPreferencesCard.test.tsx`

The Switch component is `@/components/ui/switch` (named export `Switch`). Match the visual/card style of sibling cards like `frontend/src/components/parent/GroupsCard.tsx` (read it and reuse its wrapper classes/heading markup).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/parent/__tests__/NotificationPreferencesCard.test.tsx`:
```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { NotificationPreferencesCard } from '../NotificationPreferencesCard';
import { parentApi } from '@/api/parent';

vi.mock('@/api/parent', () => ({
  parentApi: {
    getPreferences: vi.fn(),
    updatePreferences: vi.fn(),
  },
}));

function renderCard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <NotificationPreferencesCard />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(parentApi.getPreferences).mockResolvedValue({ trial_reminder_opt_out: false });
  vi.mocked(parentApi.updatePreferences).mockResolvedValue({ trial_reminder_opt_out: true });
});

describe('NotificationPreferencesCard', () => {
  it('renders the toggle ON when not opted out', async () => {
    renderCard();
    const sw = await screen.findByRole('switch', { name: /email me about my subscription/i });
    await waitFor(() => expect(sw).toBeChecked());
  });

  it('opting out calls updatePreferences(true)', async () => {
    renderCard();
    const sw = await screen.findByRole('switch', { name: /email me about my subscription/i });
    await waitFor(() => expect(sw).toBeChecked());
    fireEvent.click(sw);
    await waitFor(() =>
      expect(parentApi.updatePreferences).toHaveBeenCalledWith(true),
    );
  });

  it('has no axe violations', async () => {
    const { container } = renderCard();
    await screen.findByRole('switch');
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run (from `frontend/`): `npm run test -- NotificationPreferencesCard`
Expected: FAIL — cannot find module `../NotificationPreferencesCard`.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/parent/NotificationPreferencesCard.tsx` (adjust wrapper/heading classes to match `GroupsCard.tsx`):
```tsx
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { parentApi } from '@/api/parent';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';

export function NotificationPreferencesCard() {
  const qc = useQueryClient();
  const { toast } = useToast();

  const q = useQuery({
    queryKey: ['parent-preferences'],
    queryFn: parentApi.getPreferences,
  });

  const mutation = useMutation({
    mutationFn: (optOut: boolean) => parentApi.updatePreferences(optOut),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['parent-preferences'] });
    },
    onError: () => {
      toast({ title: 'Could not update preferences', variant: 'destructive' });
    },
  });

  const optedIn = !(q.data?.trial_reminder_opt_out ?? false);

  return (
    <section className="rounded-2xl border bg-card p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-foreground">Email preferences</h2>
      <div className="mt-4 flex items-start justify-between gap-4">
        <div>
          <label htmlFor="sub-email-toggle" className="font-medium text-foreground">
            Email me about my subscription
          </label>
          <p id="sub-email-help" className="mt-1 text-sm text-muted-foreground">
            Occasional reminders, like when a free trial is ending.
          </p>
        </div>
        <Switch
          id="sub-email-toggle"
          checked={optedIn}
          aria-describedby="sub-email-help"
          disabled={q.isLoading || mutation.isPending}
          onCheckedChange={(checked) => mutation.mutate(!checked)}
        />
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Wire into ParentDashboard**

In `frontend/src/pages/ParentDashboard.tsx`, add the import with the other component imports:
```tsx
import { NotificationPreferencesCard } from '@/components/parent/NotificationPreferencesCard';
```
Then render `<NotificationPreferencesCard />` in the dashboard body, immediately after `<SubscriptionCard />` (it sits naturally beside the subscription UI). Match surrounding wrapper markup (e.g. if `SubscriptionCard` is inside a wrapping element, mirror it).

- [ ] **Step 5: Run the component test**

Run (from `frontend/`): `npm run test -- NotificationPreferencesCard`
Expected: PASS (3 tests).

- [ ] **Step 6: Typecheck + commit**

Run: `npx tsc -b`
Expected: no errors.
```bash
git add frontend/src/components/parent/NotificationPreferencesCard.tsx frontend/src/pages/ParentDashboard.tsx frontend/src/components/parent/__tests__/NotificationPreferencesCard.test.tsx
git commit -m "feat(4c): subscription email opt-out toggle on parent dashboard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Full regression + close-out

**Files:** none (verification only)

- [ ] **Step 1: Backend lint + full test suite**

Run (from `backend/`):
```bash
/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
/Users/leeashmore/Local\ Repo/.venv/bin/pytest
```
Expected: ruff clean; all tests pass (existing + the new 4C tests). If a DB-backed test hangs ~90s+, that's the known local-Postgres environment issue — rely on CI.

- [ ] **Step 2: Frontend full gate**

Run (from `frontend/`):
```bash
npx tsc -b
npm run lint
npm run test
npm run build
```
Expected: all clean.

- [ ] **Step 3: Push**
```bash
git push origin testing
```

- [ ] **Step 4: Confirm CI green**

Watch the 5 CI jobs (frontend, backend, security, a11y, responsive) go green on the `testing` push:
```bash
gh run list --branch testing -L 1
```
Expected: success. (No `cap sync` / iOS rebuild needed — 4C touches only parent web + Settings, no native-visible surface.)

---

## Notes / Gotchas
- **No moderation** — the email is a fixed template, not LLM output, so `moderate_output` does not apply.
- **Dedupe is the cap** — one email per `(subscription, trial-end date)` via the deterministic `subject_id`; works in every environment because both `LoggingEmailSender` (dev/test) and `ResendEmailSender` (prod) write a `SentEmail` row.
- **`strftime("%A %-d %B")`** uses the `%-d` no-pad directive (valid on Linux/macOS; CI is ubuntu).
- **Cron is gated** — the new `/internal/trial-reminders/run` returns 503 until `CRON_SECRET` is set on the target backend (already true for testing + production). The cron workflow remains enabled; the new step runs alongside video-health from the next daily schedule.
