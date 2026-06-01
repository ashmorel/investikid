# Account-Based Admin Access — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Admin console reachable only by a logged-in `is_admin` user, embedded in the app; remove the static `ADMIN_TOKEN` entirely.

**Spec:** `docs/superpowers/specs/2026-06-01-account-based-admin-access-design.md`

**Tech:** FastAPI + SQLAlchemy async + Alembic (head `b1c2d3e4f5a6`); React/TS + TanStack Query; cookie session + double-submit CSRF.

---

## Task 1: `User.is_admin` + migration + grant-admin CLI

**Files:** `app/models/user.py`, `alembic/versions/<new>_add_user_is_admin.py`, `app/services/entitlements.py`, `app/cli.py`, test.

- Add `is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", default=False)` to `User`.
- Migration (down_revision `b1c2d3e4f5a6`): `op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"))`; downgrade drops it.
- `entitlements.set_admin(session, user, *, value: bool, actor: str) -> bool` mirroring `set_premium` (writes an `AuditLog`; returns whether changed).
- `cli.py`: add `grant-admin` to the dispatcher mirroring `_grant_premium` (lookup by email|username, `--revoke`, commit, print).
- Test: `set_admin` flips the flag + is idempotent.

## Task 2: Session-based admin auth + remove token + CSRF + expose is_admin

**Files:** `app/routers/admin_auth.py`, `app/core/config.py`, `app/core/csrf.py`, `app/schemas/user.py`, `app/routers/users.py`, `tests/test_config.py`.

- `admin_auth.get_current_admin`: depend on `get_current_user`; `if not (user.is_admin and user.is_active): raise HTTPException(403, "Admin access required")`; return user. Delete HTTPBearer + `settings.admin_token` usage.
- `config.py`: remove `admin_token`, `_DEFAULT_ADMIN_TOKEN`, and the `_guard_admin_token` validator.
- `tests/test_config.py`: remove the 4 admin-token guard tests.
- `csrf.py`: remove `"/admin/"` from `_DEFAULT_EXEMPT_PREFIXES`.
- `schemas/user.py`: add `is_admin: bool` to `UserProfile`. Confirm `/me` (`users.py:40`) populates it from the ORM (from_attributes).

## Task 3: Convert backend admin tests to admin-session auth

**Files:** `tests/conftest.py` (helper), `tests/test_admin_auth.py`, `tests/test_admin_modules.py`, `tests/test_admin_levels.py`, `tests/test_admin_badges_challenges.py`, `tests/test_admin_prerequisites.py`.

- Add a conftest fixture/helper `admin_client` (or `make_admin`): create a `User` with `is_admin=True`, authenticate via the existing login flow (set the access cookie like other authed tests do) and obtain the CSRF token the way other mutation tests do.
- Replace `HEADERS = {"Authorization": "Bearer test-admin-token-xyz"}` usage with the admin session (cookie + CSRF header on mutations).
- `test_admin_auth.py`: assert anonymous → 401, authenticated non-admin → 403, admin → 200.
- Add a CSRF test: an admin mutation without CSRF/trusted-origin is rejected.

## Task 4: Frontend admin client → session auth

**Files:** `src/api/admin.ts`, delete `src/lib/adminAuth.ts` + `src/components/admin/AdminLogin.tsx`, `src/api/auth.ts` (session type), `src/App.tsx` (route).

- `adminFetch`: drop the bearer token; call through the shared authenticated fetch (`apiFetch` from `client.ts`: `credentials:'include'` + `X-CSRF-Token`). Keep the 401 handling (redirect to login).
- Remove `getAdminToken`/`setAdminToken`/`clearAdminToken` usage; delete `adminAuth.ts` + `AdminLogin.tsx` + the token-login route.
- Add `is_admin: boolean` to the session/`UserProfile` type returned by `/me`.

## Task 5: Embed admin entry point + route guard

**Files:** `src/components/child/ProfileMenu.tsx` (or wherever logout lives), `src/components/admin/AdminLayout.tsx`, `src/App.tsx`.

- ProfileMenu: show an **"Admin"** link to `/admin` only when the session `is_admin`.
- `AdminLayout`: replace the stored-token gate with a check on the `/me` session query — loading → spinner; `!is_admin` (or unauthenticated) → redirect to `/login` (or home); admin → render `<Outlet/>`.

## Task 6: Frontend tests

**Files:** admin component tests + ProfileMenu test.

- Admin link renders only when `is_admin: true`.
- `AdminLayout` redirects a non-admin/anonymous session and renders children for an admin.
- `adminFetch` issues a credentialed request without an `Authorization` header (mock fetch, assert).
- Update/replace `AdminLogin` tests (component removed).

## Task 7: Full regression + security review + ship

- Backend: `ruff check .` + `pytest -q`. Frontend: `npm run lint && npx tsc -b && npm test && npm run build`.
- Security review (dispatch reviewer): CSRF now enforced on `/admin/*` mutations; no residual `admin_token`/token references anywhere; 401 anon / 403 non-admin / 200 admin; revoking `is_admin` or `is_active` immediately blocks.
- Commit per task to `main`; push; watch all 5 CI jobs green; confirm Railway deploy healthy.
- **Hand-off:** user runs `python -m app.cli grant-admin lee_ashmore@hotmail.co.uk` in Railway, then opens the app → ProfileMenu → Admin. Remove the now-unused `ADMIN_TOKEN` Railway var. iOS: `npm run build && npx cap sync ios` to carry the embedded admin entry into the native bundle.

## Self-review notes
- The single migration chains from `b1c2d3e4f5a6` — confirm `alembic heads` shows one head after.
- Removing `admin_token` also removes the `_guard_admin_token` boot check added earlier (A05-2) — that guard is obsolete once the token path is gone; the security register entry should be annotated, not left dangling.
- Admin mutations from web rely on the existing trusted-origin CSRF bypass (app.investikid.ai) — no per-call token plumbing needed beyond what `apiFetch` already does.
