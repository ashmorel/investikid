// Biometric quick-login wrapper (SP-Bio). Verify via @aparajita/capacitor-biometric-auth,
// store the opaque server secret via @aparajita/capacitor-secure-storage (biometric-gated
// where supported). Web = no-op everywhere. Plugins are dynamically imported so web bundles
// never load native code; the interface below is the ONLY surface the app depends on.
import { isNativeApp } from '@/lib/platform';

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
   * Store the opaque secret in the secure keychain under a namespaced key.
   * `whenPasscodeSetThisDeviceOnly` keeps the item off iCloud backups and out of
   * device-to-device migration, and ties its existence to a device passcode; the
   * caller-side `verify()` gate supplies the biometric check (this plugin does
   * not expose `BiometryCurrentSet` binding — see the security note in the spec).
   */
  async enroll(key: string, _label: string, secret: string): Promise<void> {
    const s = await storagePlugin();
    if (!s) return;
    await s.storage.set(ns(key), secret, false, false, s.access?.whenPasscodeSetThisDeviceOnly);
  },

  /** Read the stored secret (caller must have just verified()). Null if absent. */
  async read(key: string): Promise<string | null> {
    const s = await storagePlugin();
    if (!s) return null;
    try {
      const v = await s.storage.get(ns(key));
      return typeof v === 'string' ? v : null;
    } catch {
      return null;
    }
  },

  async clear(key: string): Promise<void> {
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
