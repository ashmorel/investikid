import { beforeEach, describe, expect, it, vi } from 'vitest';

let native = true;
vi.mock('@/lib/platform', () => ({ isNativeApp: () => native, isAndroid: () => false }));

const auth = { checkBiometry: vi.fn(), authenticate: vi.fn() };
const storage = { set: vi.fn(), get: vi.fn(), remove: vi.fn() };
vi.mock('@aparajita/capacitor-biometric-auth', () => ({ BiometricAuth: auth }));
vi.mock('@aparajita/capacitor-secure-storage', () => ({ SecureStorage: storage }));

import { biometric, getDeviceId } from '../biometric';

beforeEach(() => {
  native = true;
  localStorage.clear();
  vi.clearAllMocks();
});

describe('biometric wrapper (SP-Bio)', () => {
  it('isAvailable is false on web', async () => {
    native = false;
    expect(await biometric.isAvailable()).toBe(false);
  });

  it('isAvailable reflects the plugin', async () => {
    auth.checkBiometry.mockResolvedValue({ isAvailable: true });
    expect(await biometric.isAvailable()).toBe(true);
    auth.checkBiometry.mockResolvedValue({ isAvailable: false });
    expect(await biometric.isAvailable()).toBe(false);
  });

  it('getDeviceId is stable', () => {
    const a = getDeviceId();
    expect(a).toBeTruthy();
    expect(getDeviceId()).toBe(a);
  });

  it('verify returns true on success, false on cancel', async () => {
    auth.authenticate.mockResolvedValue(undefined);
    expect(await biometric.verify('Unlock')).toBe(true);
    auth.authenticate.mockRejectedValue(new Error('cancelled'));
    expect(await biometric.verify('Unlock')).toBe(false);
  });

  it('enroll stores the secret under a namespaced key', async () => {
    storage.set.mockResolvedValue(undefined);
    await biometric.enroll('child:1', 'Maya', 'secret-xyz');
    expect(storage.set).toHaveBeenCalledWith('bio_child_1', 'secret-xyz');
  });

  it('read returns the secret, null when biometric read fails', async () => {
    storage.get.mockResolvedValue('secret-xyz');
    expect(await biometric.read('child:1')).toBe('secret-xyz');
    storage.get.mockRejectedValue(new Error('locked'));
    expect(await biometric.read('child:1')).toBeNull();
  });

  it('clear removes the key and swallows missing-key errors', async () => {
    storage.remove.mockRejectedValue(new Error('not found'));
    await expect(biometric.clear('child:1')).resolves.toBeUndefined();
  });
});
