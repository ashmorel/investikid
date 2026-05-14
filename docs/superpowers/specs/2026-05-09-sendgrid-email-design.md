# Plan 8: Resend Email Integration

## Goal

Wire up real email delivery so parental consent emails and parent magic-link emails are actually sent. Replace the `SendGridEmailSender` stub with a `ResendEmailSender` using the Resend API (free tier, no expiry). Add HTML templates with clickable buttons.

## Scope

- Replace `SendGridEmailSender` with `ResendEmailSender` in `backend/app/services/email.py`
- Add `resend` to `requirements.txt`
- Add HTML rendering alongside existing plain-text rendering
- Add `email_from` setting to `Settings`
- Rename `sendgrid_api_key` to `resend_api_key` in Settings
- Update `email_backend` options from `"sendgrid"` to `"resend"`
- Fix `app_base_url` default (currently points to backend port 8000, but email links target frontend routes)
- Update `.env.example` and `.env` with new env vars
- Keep `LoggingEmailSender` as default for development/tests

## Architecture

### Email flow (unchanged pattern)

```
Router → get_email_sender() → EmailSender.send(session, to, template, context)
                                  ├─ LoggingEmailSender (dev/test): persist to sent_emails table
                                  └─ ResendEmailSender (production): persist to sent_emails + send via Resend API
```

Three call sites exist (unchanged):
1. `routers/auth.py:144` — consent email on child signup
2. `routers/consent.py:111` — resend consent email
3. `routers/parent_auth.py:42` — parent magic link login

### ResendEmailSender implementation

The `send()` method:
1. Renders plain text via existing `_render(template, context)`
2. Renders HTML via new `_render_html(template, context)`
3. Persists to `sent_emails` table (audit trail, same as LoggingEmailSender)
4. Sends via `resend.Emails.send()` using the `resend` Python SDK
5. Raises on API failure (let the router's error handling surface it)

The Resend SDK is synchronous by default but provides `resend.Emails.send_async()` for async contexts — perfect for our FastAPI app.

### HTML templates

Two templates, both simple and clean:

**consent_request:**
- Heading: "Approve {child_username}'s Invest-Ed account"
- Body: "{child_username} (age {age}, {country_code}) signed up and listed you as their parent."
- CTA button: "Approve Account" → links to the consent URL
- Footer: "If you didn't expect this, ignore this email. Link expires in 24 hours."

**parent_magic_link:**
- Heading: "Sign in to Invest-Ed"
- Body: "Click below to access your parent dashboard."
- CTA button: "Sign In" → links to the callback URL
- Footer: "Link expires in 15 minutes."

Both templates use inline CSS (no external stylesheets — email clients strip them). Minimal design: white background, centered card, blue CTA button. No images or logos.

### Config changes

In `Settings` (config.py):
- Add: `email_from: str = "noreply@invest-ed.app"` — the verified sender address in Resend
- Add: `resend_api_key: str = ""` — Resend API key
- Remove: `sendgrid_api_key` — no longer needed
- Change: `email_backend` options from `"logging" | "sendgrid"` to `"logging" | "resend"`
- Fix: `app_base_url: str = "http://localhost:5173"` — email links point to frontend routes (`/consent/verify`, `/parent/auth/callback`), not the backend API

In `.env`:
- `EMAIL_BACKEND=resend` (to activate)
- `RESEND_API_KEY=re_xxx` (from Resend dashboard)
- `EMAIL_FROM=noreply@invest-ed.app` (verified sender or use Resend's test domain `onboarding@resend.dev`)
- `APP_BASE_URL=http://localhost:5173` (frontend URL)

### Error handling

If Resend returns an error (bad API key, rate limit, unverified sender):
- The `send()` method raises an exception
- The calling router returns a 500-level error
- The `sent_emails` row is still created (it's flushed before the API call) but won't be committed since the transaction rolls back
- No retry logic — YAGNI for now

### Testing

- Existing tests are unaffected (they use `LoggingEmailSender` via `email_backend=logging`)
- Add a unit test for `_render_html()` that checks both templates produce valid HTML with the expected link
- Add a unit test for `ResendEmailSender.send()` that mocks `resend.Emails.send_async` and verifies:
  - Correct from/to/subject/html passed
  - `SentEmail` record created
  - `send_async` called once
- No integration test against live Resend (would need real API key)

## Files

- Modify: `backend/app/services/email.py` — replace `SendGridEmailSender` with `ResendEmailSender`, add `_render_html()`
- Modify: `backend/app/core/config.py` — add `email_from`, `resend_api_key`, remove `sendgrid_api_key`, fix `app_base_url` default
- Modify: `backend/requirements.txt` — replace `sendgrid` with `resend`
- Modify: `backend/.env.example` — document new env vars
- Create: `backend/tests/test_email.py` — unit tests for HTML rendering and Resend sender

## What does NOT change

- `EmailSender` protocol
- `LoggingEmailSender` behaviour
- `_render()` plain-text function
- The 3 router call sites
- `SentEmail` model
