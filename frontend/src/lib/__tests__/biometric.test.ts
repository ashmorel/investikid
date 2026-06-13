import { beforeEach, describe, expect, it, vi } from 'vitest';

let native = true;
vi.mock('@/lib/platform', () => ({ isNativeApp: () => native }));

const auth = { checkBiometry: vi.fn(), authenticate: vi.fn() };
// vi.mock factories are hoisted above const declarations — define the vault
// mock with vi.hoisted so it exists when the factory runs.
const vault = vi.hoisted(() => ({ isAvailable: vi.fn(), set: vi.fn(), get: vi.fn(), remove: vi.fn() }));
vi.mock('@aparajita/capacitor-biometric-auth', () => ({ BiometricAuth: auth }));
vi.mock('@/lib/biometricVault', () => ({ BiometricVault: vault }));

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

  describe('biometric-bound vault (iOS + Android)', () => {
    it('enroll writes the namespaced key to the vault', async () => {
      vault.set.mockResolvedValue(undefined);
      await biometric.enroll('child:1', 'Maya', 'secret-xyz');
      expect(vault.set).toHaveBeenCalledWith({ key: 'bio_child_1', value: 'secret-xyz' });
    });

    it('enroll is a no-op on web', async () => {
      native = false;
      await biometric.enroll('child:1', 'Maya', 'secret-xyz');
      expect(vault.set).not.toHaveBeenCalled();
    });

    it('unlockRead → ok when the vault releases the secret (no separate prompt)', async () => {
      vault.get.mockResolvedValue({ value: 'secret-xyz' });
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'ok', secret: 'secret-xyz' });
      expect(vault.get).toHaveBeenCalledWith({ key: 'bio_child_1', reason: 'Unlock' });
      expect(auth.authenticate).not.toHaveBeenCalled(); // the vault read IS the biometric prompt
    });

    it('unlockRead → gone when the item was invalidated (re-enrolled biometrics)', async () => {
      vault.get.mockResolvedValue({});
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'gone' });
    });

    it('unlockRead → cancelled when the vault read rejects (cancel/auth-fail)', async () => {
      vault.get.mockRejectedValue(new Error('AUTH_FAILED'));
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'cancelled' });
    });

    it('unlockRead → gone on web', async () => {
      native = false;
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'gone' });
      expect(vault.get).not.toHaveBeenCalled();
    });

    it('clear removes from the vault and swallows errors', async () => {
      vault.remove.mockRejectedValue(new Error('already gone'));
      await expect(biometric.clear('child:1')).resolves.toBeUndefined();
      expect(vault.remove).toHaveBeenCalledWith({ key: 'bio_child_1' });
    });
  });
});
