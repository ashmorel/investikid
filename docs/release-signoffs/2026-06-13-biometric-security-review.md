# SP-Bio Biometric Login — Security Review Record (2026-06-13)

**Feature:** Face ID / Touch ID quick-login for parent + child accounts (SP-Bio).
**Spec:** `docs/superpowers/specs/2026-06-13-biometric-login-design.md`
**Reviewed range:** `fc427fb..77ffc08` (branch `testing`); H1 closed in `907f819`.
**Verdict:** SHIP-WITH-FIXES → all fixes applied. **H1 now resolved on iOS** (biometric-bound keychain); Android carries a tracked follow-up.

## Server-side core — confirmed sound
256-bit CSPRNG secret (`secrets.token_urlsafe(32)`), only the SHA-256 hash stored, device-bound, rotated on every use (replay-safe), exchange re-checks `is_active` + `biometric_allowed` (no privilege gain after consent revoke), CSRF posture matches `/auth/login`, cross-subject isolation enforced (child secret can't mint a parent session), revocation complete across delete / master-disable / self-unenroll. No PII or secret leakage in logs or responses.

## Findings addressed in `77ffc08`
- **H2 (High):** exchange was rate-limited by IP → one shared bucket behind Railway's proxy. Now keyed per device via an `X-Device-Id` header (`biometric_exchange_key`). 256-bit secret makes brute force infeasible regardless; this fix is about DoS isolation.
- **M1 (Medium):** every successful child/parent exchange now writes an `AuditLog` row (`biometric_login` / `parent_biometric_login`) for forensic parity with login.
- **L1 (Low):** enroll endpoints now rate-limited (20/hour).
- **N1 (Nit):** exchange `secret` min_length 8 → 32.

## H1 — RESOLVED on iOS (`907f819`)

**Finding:** the secret was not bound to the current biometric set, so a re-enrolled face/fingerprint would not invalidate it — the biometric check was only an app-level gate.

**Fix (proper):** a custom in-repo Capacitor plugin, **BiometricVault** (`ios/App/App/BiometricVaultPlugin.swift` + `.m`, registered in `project.pbxproj`), stores the secret in the iOS Keychain with `SecAccessControlCreateWithFlags(kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly, .biometryCurrentSet)`. `get()` triggers the OS Face ID / Touch ID prompt and releases the secret **only** for the biometric set enrolled at write time; adding or removing a biometric invalidates the item (next `get` → `errSecItemNotFound`, surfaced to the app as `gone` → the credential is forgotten and the user must sign in with a password and re-enrol). This makes the re-enrolment guarantee **OS-enforced**, not app-enforced, and removes the separate `verify()` step on unlock (the vault read is itself the prompt).

`capacitor-native-biometric` (the only third-party plugin that exposes this) hard-declares `@capacitor/core@^3.4.3` and is unmaintained for Capacitor 8 — hence the small, dependency-free custom plugin.

**Android:** still uses `@aparajita/capacitor-secure-storage` with `whenPasscodeSetThisDeviceOnly` + `sync=false` (device-only, no backup migration) and the app-level `verify()` gate. Keystore binding (`setUserAuthenticationRequired` + `setInvalidatedByBiometricEnrollment`) is a tracked follow-up; not blocking, since the iOS TestFlight build is the only one shipping now.

**Device-QA (required at the build-4 archive):**
1. On a real device, enable Face ID sign-in (child and parent), force-quit, relaunch → confirm Face ID unlocks and re-mints the session.
2. In iOS Settings, **add a new face to Face ID** (or reset Face ID), reopen the app → confirm the app does **not** silently unlock and instead forces a password sign-in (proves `.biometryCurrentSet` invalidation).
3. Confirm cancelling the Face ID prompt leaves the app locked (does not forget the credential).
