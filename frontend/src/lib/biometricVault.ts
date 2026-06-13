import { registerPlugin } from '@capacitor/core';

/**
 * Biometric-bound secure storage (SP-Bio H1), implemented natively on both
 * platforms: `ios/App/App/BiometricVaultPlugin.swift` (Keychain
 * `SecAccessControl(.biometryCurrentSet)`) and
 * `android/.../BiometricVaultPlugin.kt` (Keystore RSA key with
 * `setInvalidatedByBiometricEnrollment`). `get` triggers the OS biometric prompt
 * and the secret is released only by the biometric set enrolled at write time —
 * adding/removing a face or fingerprint invalidates the item (the next `get`
 * resolves with no `value`).
 *
 * Native only. On web there is no implementation, so callers must gate every
 * method behind `isNativeApp()` (see `biometric.ts`) — invoking it on web
 * rejects with the standard Capacitor "not implemented" error.
 */
export interface BiometricVaultPlugin {
  isAvailable(): Promise<{ available: boolean }>;
  set(options: { key: string; value: string }): Promise<void>;
  /** Resolves `{ value }` on a biometric match, `{}` when the item is absent or
   *  invalidated, and REJECTS on user-cancel / auth-failure / lockout. */
  get(options: { key: string; reason: string }): Promise<{ value?: string | null }>;
  remove(options: { key: string }): Promise<void>;
}

export const BiometricVault = registerPlugin<BiometricVaultPlugin>('BiometricVault');
