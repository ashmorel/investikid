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

async function authPlugin() {
  if (!isNativeApp()) return null;
  try {
    return (await import('@aparajita/capacitor-biometric-auth')).BiometricAuth;
  } catch {
    return null;
  }
}

async function storagePlugin() {
  if (!isNativeApp()) return null;
  try {
    return (await import('@aparajita/capacitor-secure-storage')).SecureStorage;
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
      const info = await a.checkBiometry();
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
      await a.authenticate({ reason, cancelTitle: 'Cancel', allowDeviceCredential: false });
      return true;
    } catch {
      return false;
    }
  },

  /** Store the opaque secret in the secure keychain under a namespaced key. */
  async enroll(key: string, _label: string, secret: string): Promise<void> {
    const s = await storagePlugin();
    if (!s) return;
    await s.set(ns(key), secret);
  },

  /** Read the stored secret (caller must have just verified()). Null if absent. */
  async read(key: string): Promise<string | null> {
    const s = await storagePlugin();
    if (!s) return null;
    try {
      const v = await s.get(ns(key));
      return typeof v === 'string' ? v : null;
    } catch {
      return null;
    }
  },

  async clear(key: string): Promise<void> {
    const s = await storagePlugin();
    if (!s) return;
    try {
      await s.remove(ns(key));
    } catch {
      /* already gone */
    }
  },
};
