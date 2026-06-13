# SP-Bio Biometric Login — Security Review Record (2026-06-13)

**Feature:** Face ID / Touch ID quick-login for parent + child accounts (SP-Bio).
**Spec:** `docs/superpowers/specs/2026-06-13-biometric-login-design.md`
**Reviewed range:** `fc427fb..77ffc08` (branch `testing`).
**Verdict:** SHIP-WITH-FIXES → fixes applied in `77ffc08`. One residual (H1) needs explicit owner risk-acceptance before TestFlight.

## Server-side core — confirmed sound
256-bit CSPRNG secret (`secrets.token_urlsafe(32)`), only the SHA-256 hash stored, device-bound, rotated on every use (replay-safe), exchange re-checks `is_active` + `biometric_allowed` (no privilege gain after consent revoke), CSRF posture matches `/auth/login`, cross-subject isolation enforced (child secret can't mint a parent session), revocation complete across delete / master-disable / self-unenroll. No PII or secret leakage in logs or responses.

## Findings addressed in `77ffc08`
- **H2 (High):** exchange was rate-limited by IP → one shared bucket behind Railway's proxy. Now keyed per device via an `X-Device-Id` header (`biometric_exchange_key`). 256-bit secret makes brute force infeasible regardless; this fix is about DoS isolation.
- **M1 (Medium):** every successful child/parent exchange now writes an `AuditLog` row (`biometric_login` / `parent_biometric_login`) for forensic parity with login.
- **L1 (Low):** enroll endpoints now rate-limited (20/hour).
- **N1 (Nit):** exchange `secret` min_length 8 → 32.

## Residual — OWNER DECISION REQUIRED before TestFlight

**H1 — keychain secret is not bound to the current biometric set (`BiometryCurrentSet`).**
The chosen storage plugin (`@aparajita/capacitor-secure-storage`, selected after `capacitor-native-biometric` was rejected for a Capacitor 8 core conflict) exposes no `SecAccessControl` / biometric-set binding. Mitigation applied: the secret is now stored `whenPasscodeSetThisDeviceOnly` with `sync=false` — device-only, excluded from iCloud backup and device-to-device migration, and tied to a device passcode. The biometric check is supplied **at the app layer** by `biometric.verify()`, which always runs before the secret is read.

**Residual risk:** enrolling a *new* face/fingerprint on the device does not invalidate the stored secret (the spec's stated "re-enrolled face invalidates local secret" guarantee is not delivered cryptographically). On a shared device, someone who can both unlock the device and add their own biometric could reach the lock screen and unlock. Impact is bounded — InvestiKid holds a child's learning progress and a *practice* portfolio, no real money — and the secret remains server-revocable and rotated.

**Options for the owner:**
1. **Accept the residual** with the device-only mitigation + app-level verify gate (recommended for the practice-money beta; revisit if real money is ever introduced).
2. **Switch the storage side** to a plugin offering `kSecAccessControlBiometryCurrentSet` — reopens the Capacitor 8 dependency conflict that drove the original plugin choice.

_Pending: owner risk-acceptance (option 1) or a follow-up task (option 2). Not a CI/ship blocker for the testing environment; gate it at the build-4 TestFlight archive._
