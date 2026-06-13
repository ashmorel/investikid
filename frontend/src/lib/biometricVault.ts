import { registerPlugin } from '@capacitor/core';

/**
 * Biometric-bound secure storage (SP-Bio H1), implemented natively in
 * `ios/App/App/BiometricVaultPlugin.swift`. The iOS keychain item is created
 * with `SecAccessControl(.biometryCurrentSet)`, so `get` triggers the OS
 * biometric prompt and the secret is released only by the biometric set that
 * was enrolled at write time — adding/removing a Face ID/Touch ID enrolment
 * invalidates the item (the next `get` resolves with no `value`).
 *
 * iOS only. On Android/web there is no native implementation, so callers must
 * gate every method behind `isIOS()` (see `biometric.ts`) — invoking it
 * elsewhere rejects with the standard Capacitor "not implemented" error.
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
