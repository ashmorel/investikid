# Parent Social Login (SP-D1) — Design

**Status:** Draft for review.
**Date:** 2026-06-04
**Programme:** "Yasmin's Choice" rebrand — **SP-D of 6**, part **1 (feature)**. SP-D2 = auth-screen sky-blue polish (separate, later). SP-0/A/B/C shipped.

## Goal

Let **parents** sign in with **Sign in with Apple** and **Google** (alongside the existing magic-link), on **web and native iOS**. Children are unaffected — they keep the parent-managed username login. This is the COPPA / UK-GDPR-K-compliant choice (no child social login; provider age minimums + verifiable parental consent make child social login unsafe).

## Scope

**In (D1):** the social-login feature — backend OIDC verification + a `parent_identity` link table + sign-in/link endpoints + config; frontend provider buttons (web + native via one Capacitor plugin) + a "Connect provider" control in parent settings; security + unit tests with mocked provider tokens; a `docs/` setup guide + `.env.example` entries.

**Out (this sub-project):** auth-screen visual restyle (→ SP-D2). No change to child auth, the consent flow, or magic-link. No new parent *account-creation* path — parents still come into existence via child signup + consent; social login is parent **sign-in/linking** only. No server-side authorization-code flow / refresh tokens (ID-token verification only). No Android (web + iOS only, matching the app's platforms).

## How parent auth works today (verified — reused, not changed)

A "parent" is a **verified email** (no Parent table); a parent exists because a child registered with their `parent_email`. The parent session is a 7-day JWT in the `parent_session` httponly cookie (`issue_parent_session(email)` / `decode_parent_session` / `get_current_parent` in `app/routers/parent_auth.py` + `app/services/tokens.py`). Magic-link: `POST /parent/auth/request` (rate-limited 5/h) emails a 15-min one-time token; `GET /parent/auth/callback` consumes it and sets `parent_session` + CSRF cookies (`_set_csrf_cookie`, `_cookie_samesite` from `app/routers/auth.py`).

**Design insight:** social login is just another way to obtain a *verified parent email*; on success we reuse `issue_parent_session` → the same cookie and dashboard. No new session system.

## Architecture

### Verification model — ID-token only (no client secrets)
Apple & Google return a signed **ID token (JWT)** to the client (web JS + native SDK). The backend verifies it against the provider's public **JWKS** + allowed `aud` (our client identifiers). **No client secrets are stored** — no Apple `.p8` client-secret JWT, no Google client secret. Only *public* identifiers (client IDs / Services ID / bundle ID). `python-jose` (already a dep) does the JWT verify; JWKS fetched + cached via the existing `httpx`.

### Data model
New table `parent_identity` (hand-written, chained Alembic migration — check `alembic heads` from `backend/` first):
- `id` (uuid pk), `provider` (str: `'apple'|'google'`), `provider_subject` (str — the OIDC `sub`), `parent_email` (str, indexed), `created_at` (tz-aware).
- Unique constraint `(provider, provider_subject)`. Model in `app/models/` (new `parent_identity.py` or appended to an auth model file, following the existing SQLAlchemy 2.0 `Mapped`/`mapped_column` pattern).

### Backend services & endpoints
- **`app/services/oidc.py`** — `verify_id_token(provider, id_token, nonce) -> VerifiedIdentity{sub, email, email_verified}`. Fetches+caches the provider JWKS; verifies signature, `iss` (provider issuer), `aud` ∈ the configured allowed-audience set for that provider (web client id + ios client id for Google; Services ID + bundle id for Apple), `exp`, and the `nonce` claim. Raises typed errors (`OidcInvalid`, `OidcExpired`, `OidcAudienceMismatch`, `OidcNonceMismatch`). Pure-ish + unit-testable with injected JWKS.
- **`POST /parent/auth/oauth/{provider}`** (in `parent_auth.py`) — body `{id_token, nonce}`. Verify → resolve parent:
  1. If a `parent_identity` for `(provider, sub)` exists → use its `parent_email`.
  2. Else if `email_verified` and a `User` exists with `parent_email == email` → create the `parent_identity` link, then sign in.
  3. Else → `404`/friendly `{status: "no_parent_account"}` (no session). 
  On success: `issue_parent_session(parent_email)` + set `parent_session` + CSRF cookies (identical to magic-link callback). **Rate-limited** (e.g. `10/hour`), **nonce-protected**, **CSRF-exempt** (it bootstraps the session, like the GET callback; protected by nonce + provider signature).
- **`POST /parent/auth/oauth/{provider}/link`** — for the *currently signed-in* parent (`get_current_parent`): verify the ID token and create a `parent_identity` linking `(provider, sub)` → the signed-in `parent_email` (handles Apple Hide-My-Email: link once by `sub`, then future sign-ins match by rule 1). Idempotent.
- **`DELETE /parent/auth/oauth/{provider}/link`** — unlink (remove the row) for the signed-in parent.
- **`GET /parent/auth/identities`** — list the signed-in parent's linked providers (for the settings UI).

### Config / secrets
Add to `app/core/config.py` + `backend/.env.example` (all **public** identifiers, no secrets):
`GOOGLE_WEB_CLIENT_ID`, `GOOGLE_IOS_CLIENT_ID`, `APPLE_SERVICES_ID`, `APPLE_BUNDLE_ID`. **Never read/modify `.env`** — only document in `.env.example`. If an identifier is unset, that provider's endpoint returns a clean 503 "not configured" (so dev without creds is graceful).

### Frontend (web + native, unified)
- Add **`@capgo/capacitor-social-login`** — one plugin, same `login({provider})` API on web and native iOS (native `ASAuthorization`/Google on device; JS on web). Returns the provider ID token + the nonce we generated.
- New `src/api/parentAuth.ts` calls: `oauthSignIn(provider, idToken, nonce)`, `linkProvider`, `unlinkProvider`, `listIdentities`.
- **"Continue with Apple" / "Continue with Google"** buttons on the parent sign-in screen (`ParentLogin.tsx`), above the magic-link form, with a divider. On success → navigate to `/parent` (same as magic-link callback).
- **"Connect Apple / Google"** + unlink controls in parent settings (the parent dashboard/account area).
- Generate a cryptographically-random **nonce** per attempt; pass it to the plugin and to our endpoint for replay protection.

### Native iOS
- After adding the plugin: `npm run build && npx cap sync ios`. The iOS project needs the **Sign in with Apple capability/entitlement** and the **Google URL scheme** (reversed iOS client id). Capability enablement in Apple Developer + Xcode is part of the **user setup**; the plist/entitlement file changes are committed where they live in `ios/App/`.

## Security

- ID-token signature verified against provider JWKS (cached, refreshed on `kid` miss); strict `iss`/`aud`/`exp`/`nonce` checks; reject unverified-email auto-link (rule 2 requires `email_verified`).
- The sign-in endpoint is rate-limited + nonce-protected; it only ever issues a session for an **already-existing** parent email (no account minting). Generic error messages (no account enumeration — mirror the magic-link "queued"/"no account" neutrality where feasible).
- No secrets added (ID-token-only). `bandit` + `pip-audit` + `npm audit` (the `security` CI job) must stay green — vet `@capgo/capacitor-social-login` and any transitive deps.
- Cookies keep `httponly` + `secure` (non-dev) + the existing `SameSite` handling; native uses the `X-Capacitor-App` header pattern already in place.

## Testing

- **`oidc.py`**: unit tests with injected JWKS + crafted tokens — valid, wrong `aud`, expired, bad signature, replayed/mismatched nonce, unverified email. No network/real creds.
- **Endpoints**: `pytest` with the `client` fixture + mocked `verify_id_token` — sign-in for linked sub, auto-link on verified-email match, no-match → no session, link/unlink/list for a signed-in parent, rate-limit, CSRF-exemption. Async tests use the `loop_scope="session"` + fixtures convention.
- **Frontend**: provider buttons render + `vitest-axe`; the API client unit-tested; the plugin is mocked in tests.
- Backend `ruff`; frontend `tsc -b`/lint/test/build. All 5 CI jobs green (incl. `security`). iOS device verification by the user after they enable the capability.

## User setup (only you can do — gates real sign-in, not the build)

1. **Google Cloud Console** → OAuth consent screen; create a **Web client ID** and an **iOS client ID** (bundle `leeashmore.investikid.ai.app`).
2. **Apple Developer** → enable **Sign in with Apple** on the App ID; create a **Services ID** (web) with return URLs; enable the capability in Xcode.
3. Put the four identifiers in env (local `.env` + Railway). No secrets/keys needed (ID-token-only).
A `docs/parent-social-login-setup.md` guide is produced as part of D1.

## Decisions captured

Parents-only · ID-token-only verification (no client secrets) · reuse `issue_parent_session` (no new session model) · `parent_identity` link table (handles Apple Hide-My-Email) · `@capgo/capacitor-social-login` unified web+native · auto-link on verified-email match + explicit link from settings · account creation unchanged (child signup + consent) · D2 auth-screen polish deferred.
