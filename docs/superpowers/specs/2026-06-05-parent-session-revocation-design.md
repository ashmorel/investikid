# Parent Session — Logout & Revocation Fix (Design Spec)

**Date:** 2026-06-05
**Status:** Approved (design); ready for implementation plan
**Origin:** Security audit finding **H1** (see `docs/2026-06-05-product-review-and-backlog.md` §2). The one pre-beta security blocker.

---

## Problem

The parent session has two linked defects:

1. **Logout doesn't clear the cookie in production.** `parent_auth.logout` calls
   `response.delete_cookie(_PARENT_COOKIE, path="/")` **without** the
   `samesite`/`secure`/`httponly` attributes the cookie was *set* with
   (`_set_parent_cookies` / `magic_callback` use `samesite="none"; secure=True` in prod).
   Browsers only honour a clearing `Set-Cookie` whose attributes match the original, so
   cross-site the deletion is dropped and the parent stays signed in client-side.
   (The child `auth.logout` does this correctly — the parent path regressed it.)

2. **The parent session is non-revocable.** `issue_parent_session` (`app/services/tokens.py`)
   mints a stateless 7-day JWT with no `jti` and no DB backing. There is no revocation
   list, so a leaked/copied `parent_session` cookie is valid for a full 7 days with no way
   to kill it. The parent session gates **all** child PII (analytics, export, freeze,
   erasure, premium toggle), making it the highest-value session in the app. Child
   sessions already solve this with the `RefreshToken` table (`jti` + `revoked_at`).

## Goal

Logout reliably clears the cookie **and** invalidates the session server-side; any parent
session (e.g. a leaked/copied token) can be revoked. Match the existing child-session
architecture rather than inventing a new mechanism.

## Non-goals

- No change to child auth, OIDC verification, CSRF, or the parent-identity linking flow.
- No full short-lived-access + rotating-refresh model for parents (considered and rejected
  as overkill for the parent dashboard — see "Alternatives").
- No change to the 7-day session lifetime (acceptable once sessions are revocable).
- No "log out all my devices" UI (multi-device revocation is supported at the data layer
  but no new endpoint/UI is built now). YAGNI.

## Architecture

Introduce a DB-backed `ParentSession` record keyed by a `jti` embedded in the session JWT —
the parent-side analogue of `RefreshToken`. The JWT remains the bearer credential, but every
authenticated parent request confirms the `jti` exists and is neither revoked nor expired,
giving a real server-side kill switch. Logout revokes the current `jti` and clears the cookie
with attributes matching how it was set.

### Component A — Data model + migration

New model `ParentSession` in `app/models/parent_session.py`:

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | primary key, default `uuid4` |
| `jti` | UUID | unique, not null, indexed |
| `parent_email` | String | not null, indexed. **No FK** — the parent is identified by email (a `User.parent_email`), mirroring the existing email-keyed parent model; there is no parent `users` row to FK to. |
| `expires_at` | DateTime(tz) | not null |
| `revoked_at` | DateTime(tz) | nullable |
| `created_at` | DateTime(tz) | server default `now()`, not null |

One **hand-written, chained** Alembic migration creating `parent_sessions`, with
`down_revision = "e1f2a3b4c5d6"` (current head — verify with `alembic heads` before
writing). Index on `jti` and on `parent_email`. Downgrade drops the table.

### Component B — Token/service changes (`app/services/tokens.py`)

- `issue_parent_session` becomes **async** and takes the `AsyncSession`:
  mints a `jti` (uuid4), writes a `ParentSession` row (`expires_at = now + PARENT_SESSION_EXPIRY`),
  flushes, embeds `jti` in the JWT payload, returns the encoded token. Mirrors
  `issue_one_time_token`. TTL constant `PARENT_SESSION_EXPIRY` unchanged (7 days).
- `decode_parent_session` stays a **pure JWT verify** but returns the pair `(email, jti)`
  instead of just `email`. Raises `TokenInvalid` on a bad signature/audience, a missing
  `sub`, or a missing/malformed `jti`.
- Add `revoke_parent_session(session, jti: uuid.UUID) -> None`: sets `revoked_at = now()`
  on the matching row if present and not already revoked (idempotent; no error if absent).

### Component C — Router changes (`app/routers/parent_auth.py`)

- `_set_parent_cookies` becomes **async**, takes the `AsyncSession`, and awaits
  `issue_parent_session(session, email)`. Callers updated:
  - `oauth_sign_in` → `await _set_parent_cookies(session, response, parent_email)`.
  - `magic_callback` → `await issue_parent_session(session, record.email)` before the
    existing commit (so the row and the consumed-token commit land together).
- **`logout`** gains the request + session dependencies: read the `parent_session` cookie;
  if present, `decode_parent_session` to get the `jti` and `await revoke_parent_session(...)`
  then commit; finally `response.delete_cookie(_PARENT_COOKIE, samesite=_cookie_samesite(),
  secure=(settings.environment != "development"), httponly=True, path="/")`. Decoding
  failures are swallowed (still clear the cookie, still return `{"status": "ok"}`).
- **`get_current_parent`** → `decode_parent_session` to get `(email, jti)`, then look up the
  `ParentSession` by `jti`; raise `401` if the row is missing, `revoked_at` is set, or
  `expires_at <= now`. Otherwise return `email`. Keeps the existing `401` on missing/invalid
  cookie.

## Data flow

1. **Sign-in** (magic-link or OAuth): issue JWT with `jti` + persist `ParentSession` row →
   set cookie (`httponly; samesite=none; secure` in prod).
2. **Authenticated request**: `get_current_parent` decodes JWT → checks `ParentSession` by
   `jti` is live → yields `parent_email`.
3. **Logout**: revoke the row for the current `jti` → clear cookie with matching attributes.
4. **Revoked/expired/unknown `jti`**: `get_current_parent` → `401`.

## Error handling & edge cases

- **Tokens already in the wild at deploy time** have no `jti`, so `decode_parent_session`
  raises `TokenInvalid` → `get_current_parent` returns `401`. Effect: every currently
  signed-in parent must log in once after deploy. Acceptable, one-time.
- **Logout with a malformed/absent cookie**: no row to revoke; still clear the cookie and
  return `200`.
- **Multi-device**: each sign-in creates its own `jti`/row; logout revokes only the current
  device's session. Other devices stay signed in (mirrors child refresh tokens).
- **Clock/expiry**: expiry is enforced both by the JWT `exp` (decode) and the row
  `expires_at` (defence in depth); either failing → `401`.

## Testing (TDD)

Backend, using the existing `client`/`db_session` fixtures and
`pytestmark = pytest.mark.asyncio(loop_scope="session")`:

1. **Logout revokes server-side**: sign in → authenticated parent route works → `POST
   /parent/auth/logout` → reusing the *same* cookie on a parent route → `401`.
2. **Logout cookie-clear carries matching attributes**: assert the logout `Set-Cookie`
   header for `parent_session` includes the expiry/`Max-Age=0` clear **and** the same
   `SameSite`/`Secure` posture as login (the actual bug-fix assertion).
3. **Happy path**: a freshly issued session authenticates successfully.
4. **Revoked → 401**: revoke the row directly → parent route → `401`.
5. **Expired → 401**: a row with `expires_at` in the past → `401`.
6. **Unknown jti → 401**: a validly-signed JWT whose `jti` has no row → `401`.
7. **Sign-in persists a row**: magic-link callback and OAuth sign-in each create exactly one
   `ParentSession` row.
8. **Regression**: existing parent, OAuth/identity, compliance, and consent tests stay green.

## Alternatives considered

- **Minimal (cookie-fix + shorter TTL, stateless):** fixes defect 1 and shrinks the leaked-
  token window but provides no real kill switch. Rejected — the parent session is too high-
  value to leave non-revocable.
- **Full refresh-token rotation for parents:** maximum robustness but the largest change
  (new parent refresh endpoint + frontend session-lifecycle changes). Rejected as overkill
  for the parent dashboard; the `jti` + revocation table delivers the needed kill switch at
  a fraction of the complexity and matches the chosen-approach decision.

## Constraints

- DB change = hand-written, chained Alembic migration (check `alembic heads` first).
- Async tests use `loop_scope="session")` + `client`/`db_session` fixtures.
- Backend verify from `invest-ed/backend`: `ruff check .` + `pytest` (local Postgres can
  hang → rely on CI). Commit to `main`, end messages with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend only on
  green CI (6 jobs). No `.env` access.
- Backend-only change; no iOS rebuild needed.
