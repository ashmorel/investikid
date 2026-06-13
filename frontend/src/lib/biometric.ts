// Biometric quick-login wrapper (SP-Bio). Verify via @aparajita/capacitor-biometric-auth.
// Secret storage is platform-split (SP-Bio H1):
//   iOS     → BiometricVault, a custom plugin whose keychain item is bound to the
//             CURRENT biometric set (SecAccessControl .biometryCurrentSet) — get()
//             prompts Face ID itself and a re-enrolled face invalidates the secret.
//   Android → @aparajita/capacitor-secure-storage (device-unlock-gated); the app-level
//             verify() supplies the biometric prompt. (Keystore binding is a follow-up.)
//   Web     → no-op everywhere.
// Native plugins are dynamically imported so web bundles never load native code; the
// interface below is the ONLY surface the app depends on.
import { isIOS, isNativeApp } from '@/lib/platform';
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

async function storagePlugin() {
  if (!isNativeApp()) return null;
  try {
    const { SecureStorage, KeychainAccess } = await import('@aparajita/capacitor-secure-storage');
    return { storage: SecureStorage, access: KeychainAccess };
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
   * Store the opaque secret. iOS → BiometricVault (bound to the current biometric
   * set). Android → secure-storage with `whenPasscodeSetThisDeviceOnly` (device-only,
   * off iCloud/migration; the biometric check is the app-level verify()).
   */
  async enroll(key: string, _label: string, secret: string): Promise<void> {
    if (isIOS()) {
      await BiometricVault.set({ key: ns(key), value: secret });
      return;
    }
    const s = await storagePlugin();
    if (!s) return;
    await s.storage.set(ns(key), secret, false, false, s.access?.whenPasscodeSetThisDeviceOnly);
  },

  /**
   * Authenticate the user and return the stored secret. On iOS the OS biometric
   * prompt happens INSIDE the vault read (one prompt, no prior verify()); a
   * re-enrolled biometric set surfaces as `gone`. On Android the app-level
   * verify() is the prompt, then the secret is read from secure-storage.
   */
  async unlockRead(key: string, reason: string): Promise<UnlockResult> {
    if (isIOS()) {
      try {
        const { value } = await BiometricVault.get({ key: ns(key), reason });
        return value ? { status: 'ok', secret: value } : { status: 'gone' };
      } catch {
        return { status: 'cancelled' };
      }
    }
    if (!isNativeApp()) return { status: 'gone' };
    if (!(await this.verify(reason))) return { status: 'cancelled' };
    const s = await storagePlugin();
    if (!s) return { status: 'gone' };
    try {
      const v = await s.storage.get(ns(key));
      return typeof v === 'string' && v ? { status: 'ok', secret: v } : { status: 'gone' };
    } catch {
      return { status: 'gone' };
    }
  },

  async clear(key: string): Promise<void> {
    if (isIOS()) {
      try {
        await BiometricVault.remove({ key: ns(key) });
      } catch {
        /* already gone */
      }
      return;
    }
    const s = await storagePlugin();
    if (!s) return;
    try {
      await s.storage.remove(ns(key));
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
