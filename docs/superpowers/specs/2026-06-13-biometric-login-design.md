# Biometric Quick-Login (SP-Bio) — Design Spec

**Date:** 2026-06-13 · **Workstream:** SP-Bio (inserted feature, not part of the M1–M12
market-leader roadmap). Owner-approved via brainstorming. Holds TestFlight build 4 so the
archive ships M3–M9 + Push + Face ID together.

## Goal

Let returning users re-enter the app with Face ID / Touch ID / Android biometric instead
of retyping a password or re-doing a magic link — for **both** parent and child accounts,
with a security model appropriate for a children's app on a shared family device.

## Decisions (brainstorming)

1. **Purpose = lock + silent re-mint.** Face ID unlocks the app on launch (everyday UX);
   when the persisted session has expired (child refresh 30d / parent session 7d), Face ID
   unlocks a stored credential that silently re-mints a session — no password / magic link.
2. **Consent = hybrid double-gate (mirrors M7 push).** For children: a parent master switch
   per child (`users.biometric_allowed`, default off) → then the child enrolls on their
   device with a biometric prompt. Parents self-serve their own account.
3. **Lock timing.** Re-lock on cold launch always, and after the app has been backgrounded
   > ~2 minutes (one tunable constant). Not on every background.
4. **Credential mechanism = opaque server-issued secret** (Approach 1), stored in the
   biometric-gated keychain, hash held server-side, revocable, device-bound, rotated on use.

## Architecture (4 isolated units)

- **`app/services/biometric_service.py`** — the ONLY module touching `biometric_credentials`.
  `issue(subject, device_id, label) -> secret`, `verify_and_rotate(device_id, secret) -> subject | None`,
  `revoke(subject)` / `revoke_device(subject, device_id)`. Secret = 256-bit random; stored as
  SHA-256 hash (high-entropy → no bcrypt). Rotates the secret on each successful verify.
- **Auth endpoints** — child under `/auth/biometric/*`, parent under `/parent/auth/biometric/*`
  (matches existing split: child auth in `auth.py`, parent in `parent_auth.py`). All delegate
  to the service.
- **`frontend/src/lib/biometric.ts`** — thin wrapper over the native plugin:
  `isAvailable()`, `verify(reason)`, `enroll(key, label, secret)`, `read(key)`, `clear(key)`.
  Web returns "unavailable" everywhere (feature no-ops). Interface kept minimal so the plugin
  choice is swappable.
- **`frontend/src/components/auth/BiometricGate.tsx`** — the lock-screen state machine
  wrapping the authenticated shell.

## Native plugin

`capacitor-native-biometric` (availability check + biometric verify + secure keychain
credential storage in one). **Plan must verify Capacitor 8 compatibility**; if not C8-ready,
fall back to `@aparajita/capacitor-biometric-auth` (verify) + a secure-storage plugin behind
the same `biometric.ts` interface. Required iOS config: `NSFaceIDUsageDescription` in
`Info.plist` ("Use Face ID to unlock InvestiKid and sign in faster."). Android: biometric
permission (added by the plugin). One extra `cap sync ios`; folds into the existing build 4
(no further version bump — build 4 is un-archived).

## Backend

### Model (`app/models/biometric.py`)
`BiometricCredential`:
- `id` UUID PK
- `subject_kind` String(10) — `'child'` | `'parent'`
- `user_id` UUID FK users.id CASCADE, nullable (set for child — keeps CASCADE on child delete)
- `parent_email` String(255), nullable, indexed (set for parent)
- `subject_key` String(80), indexed — `f"child:{user_id}"` or `f"parent:{email}"`; the
  NULL-free identity column used for the unique constraint and lookups (a composite unique
  over the nullable user_id/parent_email would NOT enforce uniqueness for parent rows, since
  Postgres treats NULLs as distinct).
- `device_id` String(64) — client-generated stable per-install id
- `label` String(60) — display name for the lock-screen list (child username / "Parent")
- `secret_hash` String(64) — SHA-256 hex
- `expires_at` DateTime(tz) — issue + ~90 days
- `last_used_at` DateTime(tz), nullable
- `created_at` DateTime(tz)
- `revoked_at` DateTime(tz), nullable
- UniqueConstraint (device_id, subject_key) so re-enroll on the same device replaces.

`users.biometric_allowed` Boolean, default/server_default false (child master switch).

Migration chained off `d1e2f3a4b5c6`; **full-chain scratch-Postgres replay before push**
(the standing rule after the M8 outage).

### Endpoints
- `POST /auth/biometric/enroll` (child session, CSRF) → 403 unless `current_user.biometric_allowed`;
  body `{device_id, label}`; returns `{secret}` once. Audited.
- `POST /auth/biometric/exchange` (no prior session; same CSRF posture as `/auth/login` — an
  unauthenticated cookie-setting entry point; rate-limited e.g. `10/hour` keyed by device_id) →
  body `{device_id, secret}`; `verify_and_rotate`; re-check the child is active + consent given
  (`biometric_allowed` still true); on success set child access+refresh+csrf cookies (reuse
  `_issue_refresh_token`) and return `{secret: <rotated>}` so the client updates the keychain.
- `DELETE /auth/biometric/devices/{device_id}` (child session) → revoke this device's child cred.
- `POST /parent/auth/biometric/enroll` (parent session) → parents always allowed; returns secret.
- `POST /parent/auth/biometric/exchange` (no prior session; CSRF posture matching the parent
  magic-link callback; rate-limited) → `verify_and_rotate`; re-check the `parent_email` still
  owns ≥1 non-deleted child (same guard the magic-link callback applies); issue a parent session
  (reuse `issue_parent_session`); rotate; return the new secret.
- `DELETE /parent/auth/biometric/devices/{device_id}` (parent session) → revoke.
- `POST /parent/children/{id}/biometric` (parent session) → `{enabled}`; flips
  `users.biometric_allowed`; on **disable**, also `biometric_service.revoke(child)` so all the
  child's stored secrets die immediately. Audited, IDOR-safe (mirrors the push toggle exactly).
- `ChildOut` += `biometric_allowed`; `UserProfile` (child `/me`) += `biometric_allowed`.

### Revocation integration
- `account_deletion_service` revokes the subject's biometric rows (child + parent paths).
- Parent master-disable revokes (above).
- Exchange always re-checks live account state, so a dead account → 401 → client clears keychain
  + falls back to full login.

## Frontend

### `lib/biometric.ts`
Wraps the plugin; `device_id` generated once and persisted (localStorage). Keychain key scheme:
`bio:<subject_kind>:<id>` so multiple accounts coexist on one device. `read()` triggers the OS
biometric prompt; failure/cancel surfaces a typed result, never throws into the UI.

### `<BiometricGate>`
Wraps the authed shell (inside the router, outside page content). State:
`checking | disabled | locked | unlocking | unlocked`.
- `disabled` when: web, no hardware, or no enrolled credential for any account on this device →
  render children directly (no gate).
- Locks on mount (cold launch) and via `@capacitor/app` `appStateChange`: stamp `backgroundedAt`
  on background; on resume, if `now - backgroundedAt > LOCK_TIMEOUT_MS` (~120s) → `locked`.
- `locked` screen: Penny + "Welcome back" + the enrolled account(s) as tappable rows (label).
  Tap → `unlocking` → `biometric.read(key)` (Face ID) → if current session valid, `unlocked`;
  else `POST /…/exchange` → on 200 `unlocked`, on 401 clear that key + show "Sign in" escape.
  Biometric cancel/fail → back to `locked` with a "Sign in differently" link to full login.
- a11y: focusable account buttons ≥44px, `aria-live` on unlock status, axe-clean.

### Consent toggles
- Parent dashboard `ChildCard`: a "Face ID sign-in" switch next to the push/premium switches
  (calls `POST /parent/children/{id}/biometric`; optimistic, same pattern as push).
- Child ProfileMenu: a "Sign in with Face ID" toggle shown ONLY when `me.biometric_allowed`
  && native && hardware available. On → `biometric.verify()` then `enroll` (store secret); off
  → `DELETE devices/{id}` + `clear` keychain.
- Parent's own account: an equivalent enroll/unenroll toggle in parent settings (self-serve).

## Security review

A dedicated security-review pass is part of the plan (new credential path in a kids' app),
covering: opaque-secret entropy + hashing, device binding + rotation defeats replay, rate-limit
on exchange, exchange re-checks active/consent (no privilege gain over normal login),
keychain `BiometryCurrentSet` (re-enrolled face invalidates local secret), no PII in tokens,
revocation completeness (delete/disable/unenroll), and CSRF posture parity with existing entry
points.

## Edge cases

- No hardware / not enrolled on device → toggle hidden, gate `disabled`.
- Biometric lockout (OS too-many-fails) → `verify` fails → "Sign in differently".
- Parent disables / account deleted while enrolled → exchange 401 → keychain cleared, full login.
- Multiple accounts enrolled on one device → lock screen lists each.
- Web / Android-without-biometric → whole feature no-ops.
- Secret rotation race (two exchanges) → second presents a stale secret → 401 → re-login (safe).

## Testing

**Backend:** enroll requires consent (child) / always (parent); exchange happy, expired,
revoked, wrong-device, rotated-secret-on-reuse, re-check active+consent; parent-disable revokes
child creds; account-deletion revokes; rate-limit; audit rows. **Frontend:** gate state machine
(cold-launch lock, 2-min background re-lock, unlock-valid-session, unlock-expired→exchange,
biometric-fail escape, web/no-enroll → disabled); consent toggles (master gates child toggle
visibility, enroll/unenroll calls); lock-screen account list; axe on lock screen + toggles.
Native plugin mocked; real Face ID verified in manual device QA on the resulting build.
Full repo gates (ruff+pytest; tsc+lint+vitest+build), then `cap sync ios`.

## Out of scope

App-PIN fallback (rely on OS passcode + full login) · biometric for the public `/try` demo ·
per-surface re-auth beyond the launch gate · cross-device credential sync.
