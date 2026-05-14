# Resend Email Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up real email delivery so parental consent and parent magic-link emails are actually sent, using Resend (free tier, no expiry).

**Architecture:** Replace the `SendGridEmailSender` stub with `ResendEmailSender` using the Resend Python SDK (`resend.Emails.send_async()`). Add `_render_html()` for HTML email bodies with clickable CTA buttons. Both senders persist to `sent_emails` for audit. Config gets `email_from`, renames `sendgrid_api_key` to `resend_api_key`, and fixes `app_base_url` default.

**Tech Stack:** Python, resend SDK, FastAPI, SQLAlchemy, pytest

---

### Task 1: Config changes and dependency

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add `email_from` setting, rename `sendgrid_api_key`, update `email_backend` comment, and fix `app_base_url` default**

In `backend/app/core/config.py`, make four changes:

Replace:
```python
    sendgrid_api_key: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    email_backend: str = "logging"  # "logging" | "sendgrid"
    app_base_url: str = "http://localhost:8000"
```

With:
```python
    resend_api_key: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    email_backend: str = "logging"  # "logging" | "resend"
    email_from: str = "noreply@invest-ed.app"
    app_base_url: str = "http://localhost:5173"
```

The `app_base_url` change is necessary because the email links point to frontend routes (`/consent/verify`, `/parent/auth/callback`), not backend API endpoints. The `email_from` is the verified sender address in Resend.

- [ ] **Step 2: Add `resend` to requirements.txt**

In `backend/requirements.txt`, add `resend` after the existing `httpx` line (before the `# dev/test` section):

```
resend==2.5.0
```

- [ ] **Step 3: Update `.env.example`**

Replace the entire content of `backend/.env.example` with:

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/investedb
TEST_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/investedb_test
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-me-to-a-long-random-string-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
ENVIRONMENT=development
RESEND_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
EMAIL_BACKEND=logging
EMAIL_FROM=noreply@invest-ed.app
APP_BASE_URL=http://localhost:5173
```

- [ ] **Step 4: Install the dependency**

Run: `cd backend && pip install resend==2.5.0`

Expected: successful install.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/requirements.txt backend/.env.example
git commit -m "config: add email_from, rename to resend_api_key, fix app_base_url default, add resend dependency"
```

---

### Task 2: HTML email templates

**Files:**
- Modify: `backend/app/services/email.py`
- Create: `backend/tests/test_email.py`

- [ ] **Step 1: Write failing tests for `_render_html()`**

Create `backend/tests/test_email.py`:

```python
import pytest

from app.services.email import _render_html


def test_render_html_consent_request():
    context = {
        "child_username": "alice",
        "age": 13,
        "country_code": "GB",
        "link": "http://localhost:5173/consent/verify?token=abc123",
    }
    html = _render_html("consent_request", context)

    assert "alice" in html
    assert "13" in html
    assert "GB" in html
    assert 'href="http://localhost:5173/consent/verify?token=abc123"' in html
    assert "Approve Account" in html
    assert "24 hours" in html
    assert "<html" in html


def test_render_html_parent_magic_link():
    context = {
        "link": "http://localhost:5173/parent/auth/callback?token=xyz789",
    }
    html = _render_html("parent_magic_link", context)

    assert 'href="http://localhost:5173/parent/auth/callback?token=xyz789"' in html
    assert "Sign In" in html
    assert "15 minutes" in html
    assert "<html" in html


def test_render_html_unknown_template():
    with pytest.raises(ValueError, match="Unknown template"):
        _render_html("nonexistent", {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_email.py -v`
Expected: FAIL — `_render_html` not found (ImportError).

- [ ] **Step 3: Implement `_render_html()` and `_email_subject()`**

In `backend/app/services/email.py`, add these two functions after the existing `_render` function (after line 33, before `class LoggingEmailSender`):

```python
_SUBJECT = {
    "consent_request": "Approve your child's Invest-Ed account",
    "parent_magic_link": "Sign in to Invest-Ed",
}


def _email_subject(template: str) -> str:
    return _SUBJECT.get(template, "Invest-Ed")


def _render_html(template: str, context: dict) -> str:
    if template == "consent_request":
        heading = f"Approve {context['child_username']}'s Invest-Ed account"
        body_text = (
            f"{context['child_username']} (age {context['age']}, {context['country_code']}) "
            f"signed up for Invest-Ed and listed you as their parent."
        )
        cta_label = "Approve Account"
        cta_url = context["link"]
        footer = "If you didn't expect this, you can ignore this email. Link expires in 24 hours."
    elif template == "parent_magic_link":
        heading = "Sign in to Invest-Ed"
        body_text = "Click below to access your parent dashboard."
        cta_label = "Sign In"
        cta_url = context["link"]
        footer = "Link expires in 15 minutes."
    else:
        raise ValueError(f"Unknown template: {template}")

    return (
        '<!DOCTYPE html>'
        '<html lang="en">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "</head>"
        '<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td align="center" style="padding:40px 20px;">'
        '<table role="presentation" width="100%" style="max-width:480px;background:#ffffff;border-radius:8px;overflow:hidden;">'
        '<tr><td style="padding:32px 24px;">'
        f'<h1 style="margin:0 0 16px;font-size:20px;color:#111827;">{heading}</h1>'
        f'<p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#374151;">{body_text}</p>'
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">'
        '<tr><td align="center" style="border-radius:6px;background-color:#2563eb;">'
        f'<a href="{cta_url}" target="_blank" '
        'style="display:inline-block;padding:12px 24px;font-size:15px;'
        f'font-weight:600;color:#ffffff;text-decoration:none;">{cta_label}</a>'
        "</td></tr></table>"
        f'<p style="margin:24px 0 0;font-size:13px;color:#6b7280;">{footer}</p>'
        "</td></tr></table>"
        "</td></tr></table>"
        "</body></html>"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_email.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/email.py backend/tests/test_email.py
git commit -m "feat: add HTML email templates with _render_html()"
```

---

### Task 3: Implement ResendEmailSender

**Files:**
- Modify: `backend/app/services/email.py`
- Modify: `backend/tests/test_email.py`

- [ ] **Step 1: Write failing test for ResendEmailSender**

Append to `backend/tests/test_email.py`:

```python
from unittest.mock import AsyncMock, patch

from app.services.email import ResendEmailSender

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_resend_sender_calls_api_and_persists(db_session):
    sender = ResendEmailSender(api_key="re_fake", from_email="test@example.com")

    context = {
        "child_username": "bob",
        "age": 12,
        "country_code": "GB",
        "link": "http://localhost:5173/consent/verify?token=tok123",
    }

    with patch("app.services.email.resend") as mock_resend:
        mock_resend.Emails.send_async = AsyncMock(return_value={"id": "msg_123"})

        await sender.send(db_session, "parent@example.com", "consent_request", context)

        # Verify resend was called once with correct params
        mock_resend.Emails.send_async.assert_called_once()
        call_params = mock_resend.Emails.send_async.call_args[0][0]
        assert call_params["from"] == "test@example.com"
        assert call_params["to"] == ["parent@example.com"]
        assert call_params["subject"] == "Approve your child's Invest-Ed account"
        assert "bob" in call_params["html"]
        assert "bob" in call_params["text"]

    # Verify SentEmail record was created
    from sqlalchemy import select, func
    from app.models.consent import SentEmail
    count = await db_session.scalar(select(func.count()).select_from(SentEmail))
    assert count == 1

    row = await db_session.scalar(select(SentEmail))
    assert row.to_email == "parent@example.com"
    assert row.template == "consent_request"
    assert "bob" in row.body


async def test_resend_sender_raises_on_api_error(db_session):
    sender = ResendEmailSender(api_key="re_fake", from_email="test@example.com")

    context = {
        "link": "http://localhost:5173/parent/auth/callback?token=tok456",
    }

    with patch("app.services.email.resend") as mock_resend:
        mock_resend.Emails.send_async = AsyncMock(
            side_effect=Exception("Resend API error")
        )

        with pytest.raises(Exception, match="Resend API error"):
            await sender.send(
                db_session, "parent@example.com", "parent_magic_link", context
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_email.py -v`
Expected: New tests FAIL — `ResendEmailSender` not found (ImportError).

- [ ] **Step 3: Implement ResendEmailSender**

In `backend/app/services/email.py`, add the `resend` import at the top of the file (after the existing imports):

```python
import resend
```

Then replace the existing `SendGridEmailSender` class (lines 47-51) with:

```python
class ResendEmailSender:
    """Sends real emails via Resend API. Also persists to sent_emails for audit."""

    def __init__(self, api_key: str, from_email: str) -> None:
        self._api_key = api_key
        self._from_email = from_email

    async def send(
        self, session: AsyncSession, to: str, template: str, context: dict
    ) -> None:
        plain = _render(template, context)
        html = _render_html(template, context)
        subject = _email_subject(template)

        # Persist audit record (same as LoggingEmailSender)
        session.add(SentEmail(to_email=to, template=template, body=plain))
        await session.flush()

        # Send via Resend
        resend.api_key = self._api_key
        params: resend.Emails.SendParams = {
            "from": self._from_email,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": plain,
        }
        await resend.Emails.send_async(params)
```

- [ ] **Step 4: Update `get_email_sender()` to use ResendEmailSender**

Replace the existing `get_email_sender()` function:

```python
def get_email_sender() -> EmailSender:
    from app.core.config import settings
    if settings.email_backend == "resend":
        return ResendEmailSender(
            api_key=settings.resend_api_key,
            from_email=settings.email_from,
        )
    return LoggingEmailSender()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_email.py -v`
Expected: 5 PASSED.

- [ ] **Step 6: Run the full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass. Existing tests are unaffected because they use `email_backend=logging`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/email.py backend/tests/test_email.py
git commit -m "feat: implement ResendEmailSender with API integration and audit trail"
```

---

### Task 4: Update `.env` and verify end-to-end

**Files:**
- Modify: `backend/.env` (add new env vars only — do NOT read or expose existing secrets)

- [ ] **Step 1: Add new env vars to `.env`**

Append these lines to `backend/.env` (do NOT modify existing lines, do NOT read the file first):

```
EMAIL_BACKEND=logging
EMAIL_FROM=noreply@invest-ed.app
APP_BASE_URL=http://localhost:5173
```

Also find and replace the existing `SENDGRID_API_KEY=` line with `RESEND_API_KEY=`:

Run: `cd backend && sed -i '' 's/^SENDGRID_API_KEY=/RESEND_API_KEY=/' .env`

Note: `EMAIL_BACKEND` stays as `logging` for local development. Change to `resend` when you have a real Resend API key configured.

- [ ] **Step 2: Verify the app starts**

Run: `cd backend && timeout 5 uvicorn app.main:app --port 8001 2>&1 || true`
Expected: App starts without import errors. The `resend` import in `email.py` should resolve.

- [ ] **Step 3: Run the full test suite one more time**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/.env
git commit -m "config: add email settings to .env for local development"
```
