# Account-Based Admin Access — Design Spec

## Goal

Replace the shared static `ADMIN_TOKEN` bearer auth for the admin console with **account-based access**: the admin console is embedded in the app and reachable only by a logged-in user whose account has `is_admin = True`. The static token path is **removed entirely** (no break-glass).

## Context (verified 2026-06-01)

- Single `User` model (`app/models/user.py`) — username + `password_hash` (+ optional `email`), `is_premium`. No separate parent/admin account type; "parents" are a `parent_email` on a child row (magic-link only).
- Admin router (`app/routers/admin.py`) is gated by `dependencies=[Depends(get_current_admin)]`. `get_current_admin` (`app/routers/admin_auth.py`) currently checks `Authorization: Bearer <settings.admin_token>` (HTTPBearer).
- `settings.admin_token` defaults to `test-admin-token-xyz`; a `Settings._guard_admin_token` validator (config.py) fails prod boot on the default. **Both become obsolete and are removed.**
- CSRF (`app/core/csrf.py`): `/admin/` is a CSRF-exempt **prefix** (`_DEFAULT_EXEMPT_PREFIXES`). Safe today only because bearer-token auth isn't cookie-based.
- Normal session auth: `get_current_user` (`app/routers/users.py:16`) reads the httpOnly access cookie. Cross-domain CSRF already solved via trusted-origin bypass + `X-Capacitor-App` (`csrf.py`).
- `/me` → `UserProfile` schema (`app/schemas/user.py`, has `is_premium`).
- Frontend admin auth: `src/lib/adminAuth.ts` (token storage) + `AdminLogin.tsx` (token paste) + `adminFetch` (`src/api/admin.ts`) sending `Authorization: Bearer <token>` to `${API_BASE}/admin/...`. `AdminLayout.tsx` gates on a stored token.
- Existing admin backend tests authenticate via `Authorization: Bearer test-admin-token-xyz` across: `test_admin_auth.py`, `test_admin_modules.py`, `test_admin_levels.py`, `test_admin_badges_challenges.py`, `test_admin_prerequisites.py`.

## Design

### Backend

1. **`User.is_admin`** — new `Boolean`, `nullable=False`, `server_default="false"`, default `False`. One Alembic migration chaining from head `b1c2d3e4f5a6`.

2. **Grant mechanism** — `set_admin(session, user, *, value, actor)` helper (in `app/services/entitlements.py`, mirroring `set_premium`, with an `AuditLog` row). CLI subcommand `python -m app.cli grant-admin <email|username> [--revoke]` mirroring `grant-premium`.

3. **`get_current_admin` rewrite** (`admin_auth.py`) — depends on `get_current_user`; require `user.is_admin and user.is_active`, else `403 Forbidden`. Remove all HTTPBearer / `settings.admin_token` logic. Returns the admin `User`.

4. **Remove the static token** — delete `admin_token` from `Settings`, delete the `_guard_admin_token` validator + its `test_config.py` cases, and remove the `_DEFAULT_ADMIN_TOKEN` constant. (No env var needed any more; document the removal.)

5. **Remove `/admin/` from CSRF exemption** — drop `"/admin/"` from `_DEFAULT_EXEMPT_PREFIXES`. Admin mutations now flow through the same double-submit CSRF check as all other authenticated mutations (trusted-origin bypass covers web `app.investikid.ai`; `X-Capacitor-App` covers native). Verify no other exempt entry depends on `/admin/`.

6. **Expose `is_admin`** — add `is_admin: bool` to `UserProfile` so `/me` reports it. The frontend uses this to show the Admin entry point and guard the route.

### Frontend

7. **`adminFetch` uses the session, not a token** — route admin calls through the normal authenticated flow (`credentials: 'include'` + `X-CSRF-Token`, i.e. reuse `apiFetch` from `client.ts`). Delete `src/lib/adminAuth.ts`, the token-paste `AdminLogin.tsx`, and the `/admin` token-login screen.

8. **Embed the admin entry point** — surface an **"Admin"** link in the child `ProfileMenu` (next to logout) shown only when the session's `is_admin` is true. `AdminLayout` guards on `is_admin` from the `/me` session query: non-admins (or logged-out) are redirected to the normal login / home; admins render the dashboard.

9. **Session type** — add `is_admin` to the frontend session/`UserProfile` type and the `useChildSession`/`/me` query so the link + guard can read it.

### Security

- Admin authorization re-evaluated every request (current user + `is_admin` + `is_active`); revoking admin or deactivating the account kills access immediately.
- No shared secret anywhere. Recovery if locked out = existing password-reset flow or a server-side `grant-admin` re-run (operator has Railway access). Accepted: no break-glass token.
- Reuses audited password verification + lockout (sub-project 1/2) — no new credential path.
- End-of-feature security review: confirm CSRF now enforced on `/admin/*` mutations, no residual token references, admin endpoints 403 for non-admin authenticated users and 401 for anonymous.

## API / behaviour changes

- `GET /me` response gains `is_admin`.
- All `/admin/*` endpoints: auth changes from bearer token → admin session; mutations now require the CSRF header (web trusted-origin handles this transparently).
- New CLI: `grant-admin` / `--revoke`.
- Removed: `ADMIN_TOKEN` env var, the token login screen.

## Testing

- **Backend:** convert the 5 admin test files from the bearer header to an authenticated **admin-user session** (add a conftest helper that creates an `is_admin` user + logs in / sets the access cookie + CSRF). Assert: non-admin authenticated user → 403; anonymous → 401; admin → 200. `grant-admin` CLI flips `is_admin`. `/me` returns `is_admin`. A CSRF test that an admin mutation without the header/trusted-origin is rejected. Remove obsolete `admin_token` config tests.
- **Frontend:** Admin link renders only when `is_admin`; `AdminLayout` redirects non-admins; `adminFetch` issues session-credentialed requests (no bearer). Update/replace `AdminLogin` tests.
- CI (5 jobs) green; Railway deploys on green.

## Out of scope

- Admin password reset UI (use the existing reset flow), MFA, an in-app admin-management UI to grant admin (CLI only for now).
- Migrating away from the single `User` model.
