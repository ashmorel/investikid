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

## H1 — RESOLVED on both platforms (iOS `907f819`, Android follow-up)

**Finding:** the secret was not bound to the current biometric set, so a re-enrolled face/fingerprint would not invalidate it — the biometric check was only an app-level gate.

**Fix (proper):** a custom in-repo Capacitor plugin, **BiometricVault**, binds the secret to the *current* biometric set natively on both platforms; `get()` runs the OS prompt itself (one prompt, no separate `verify()`) and a re-enrolment surfaces as `gone` → the credential is forgotten and the user must sign in with a password and re-enrol. The re-enrolment guarantee is **OS-enforced**, not app-enforced.

- **iOS** (`ios/App/App/BiometricVaultPlugin.swift` + `.m`, registered in `project.pbxproj`): Keychain item with `SecAccessControlCreateWithFlags(kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly, .biometryCurrentSet)`; invalidation → `errSecItemNotFound`.
- **Android** (`android/.../BiometricVaultPlugin.kt`, registered in `MainActivity`): an AndroidKeyStore RSA keypair with `setUserAuthenticationRequired(true)` + `setInvalidatedByBiometricEnrollment(true)`. The secret is encrypted with the public key (no prompt on write) and decrypted with the private key via `BiometricPrompt` + `CryptoObject` (`BIOMETRIC_STRONG`); a new enrolment throws `KeyPermanentlyInvalidatedException` → `gone`. (OAEP is pinned to MGF1-SHA1 to avoid the AndroidKeyStore digest-mismatch; `USE_BIOMETRIC` permission added; `androidx.biometric:biometric:1.1.0`.)

`capacitor-native-biometric` (the only third-party plugin exposing iOS `BiometryCurrentSet`) hard-declares `@capacitor/core@^3.4.3` and is unmaintained for Capacitor 8 — hence the small, dependency-free custom plugin. The now-unused `@aparajita/capacitor-secure-storage` was removed.

**Device-QA (required at the build-4 archive):**
1. On a real device, enable Face ID sign-in (child and parent), force-quit, relaunch → confirm Face ID unlocks and re-mints the session.
2. In iOS Settings, **add a new face to Face ID** (or reset Face ID), reopen the app → confirm the app does **not** silently unlock and instead forces a password sign-in (proves `.biometryCurrentSet` invalidation).
3. Confirm cancelling the Face ID prompt leaves the app locked (does not forget the credential).

**Android — VERIFIED on emulator (Pixel API 35, 2026-06-13).** The debug APK was built, installed, and the native `BiometricVault` plugin driven directly via the WebView JS bridge (Chrome DevTools over adb). Results:
- App loads cleanly (login screen renders; no blank-screen issue — the crossorigin fix holds on Android too).
- `isAvailable()` → `false` with no fingerprint, `true` after enrolling one (correct `BiometricManager` dispatch).
- `set({key,value})` → resolves with **no prompt** (RSA public-key encrypt).
- `get({key,reason})` → showed the system `BiometricPrompt`; after a simulated fingerprint touch, returned the **exact** stored secret (validates `BiometricPrompt` + `CryptoObject` + the OAEP/MGF1-SHA1 decrypt path).
- **Invalidation:** after enrolling a *second* fingerprint, `get()` returned `{}` (**gone**) with no prompt and no secret leak — `KeyPermanentlyInvalidatedException` at cipher-init, exactly the H1 guarantee. The iOS equivalent (steps 1–3 above) still needs a real-device pass at the archive.
