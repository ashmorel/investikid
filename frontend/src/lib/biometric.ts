// Biometric quick-login wrapper (SP-Bio). Availability + the enroll-confirm prompt
// use @aparajita/capacitor-biometric-auth. Secret storage uses BiometricVault, a
// custom plugin that binds the secret to the CURRENT biometric set on both natives
// (SP-Bio H1): iOS keychain `SecAccessControl(.biometryCurrentSet)`, Android Keystore
// `setInvalidatedByBiometricEnrollment`. get() runs the OS prompt itself and a
// re-enrolled face/fingerprint invalidates the secret. Web = no-op everywhere.
// The biometric-auth plugin is dynamically imported so web bundles never load native
// code; the interface below is the ONLY surface the app depends on.
import { isNativeApp } from '@/lib/platform';
import { BiometricVault } from '@/lib/biometricVault';

/** Outcome of an authenticated secret read (see `biometric.unlockRead`). */
export type UnlockResult =
  | { status: 'ok'; secret: string }
  | { status: 'cancelled' } // user cancelled / auth failed / locked out → stay locked, keep credential
  | { status: 'gone' }; // secret absent or invalidated (e.g. re-enrolled biometrics) → forget credential

const DEVICE_KEY = 'bio-device-id';
const ns = (key: string) => `bio_${key.replace(/[^a-zA-Z0-9_]/g, '_')}`;

export function getDeviceId(): string {
  let id = localStorage.getItem(DEVICE_KEY);
  if (!id) {
    id = crypto.randomUUID?.() ?? `dev-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem(DEVICE_KEY, id);
  }
  return id;
}

// Capacitor plugin proxies report a callable for EVERY property (the native
// method shim), so an unawaited proxy looks "thenable" — returning one as the
// resolved value of an async function makes the runtime probe `.then` on it and
// the web proxy rejects with UNIMPLEMENTED. Wrap the proxy in a plain object so
// the resolved value is never itself thenable.
async function authPlugin() {
  if (!isNativeApp()) return null;
  try {
    const { BiometricAuth } = await import('@aparajita/capacitor-biometric-auth');
    return { auth: BiometricAuth };
  } catch {
    return null;
  }
}

export const biometric = {
  /** True only on a native device with usable biometric hardware enrolled. */
  async isAvailable(): Promise<boolean> {
    const a = await authPlugin();
    if (!a) return false;
    try {
      const info = await a.auth.checkBiometry();
      return Boolean(info.isAvailable);
    } catch {
      return false;
    }
  },

  /** Prompt Face ID / Touch ID; resolves true on success, false on cancel/fail. */
  async verify(reason: string): Promise<boolean> {
    const a = await authPlugin();
    if (!a) return false;
    try {
      await a.auth.authenticate({ reason, cancelTitle: 'Cancel', allowDeviceCredential: false });
      return true;
    } catch {
      return false;
    }
  },

  /**
   * Store the opaque secret in the biometric-bound vault (iOS keychain /
   * Android Keystore). No prompt — writing is unauthenticated; the biometric
   * gate is on read. Web is a no-op.
   */
  async enroll(key: string, _label: string, secret: string): Promise<void> {
    if (!isNativeApp()) return;
    await BiometricVault.set({ key: ns(key), value: secret });
  },

  /**
   * Authenticate the user and return the stored secret. The OS biometric prompt
   * happens INSIDE the vault read (one prompt, no separate verify()), and a
   * re-enrolled biometric set surfaces as `gone`. Web returns `gone`.
   */
  async unlockRead(key: string, reason: string): Promise<UnlockResult> {
    if (!isNativeApp()) return { status: 'gone' };
    try {
      const { value } = await BiometricVault.get({ key: ns(key), reason });
      return value ? { status: 'ok', secret: value } : { status: 'gone' };
    } catch {
      return { status: 'cancelled' };
    }
  },

  async clear(key: string): Promise<void> {
    if (!isNativeApp()) return;
    try {
      await BiometricVault.remove({ key: ns(key) });
    } catch {
      /* already gone */
    }
  },
};


// ── Enrolled-account registry (lock-screen list) ───────────────────
export type BioAccount = { key: string; label: string; kind: 'child' | 'parent' };
const ACCOUNTS_KEY = 'bio-accounts';

export function getBioAccounts(): BioAccount[] {
  try {
    const raw = localStorage.getItem(ACCOUNTS_KEY);
    return raw ? (JSON.parse(raw) as BioAccount[]) : [];
  } catch {
    return [];
  }
}

export function addBioAccount(acc: BioAccount): void {
  const list = getBioAccounts().filter((a) => a.key !== acc.key);
  list.push(acc);
  localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(list));
}

export function removeBioAccount(key: string): void {
  localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(getBioAccounts().filter((a) => a.key !== key)));
}
