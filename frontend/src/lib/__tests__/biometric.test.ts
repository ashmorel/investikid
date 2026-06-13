import { beforeEach, describe, expect, it, vi } from 'vitest';

let native = true;
let ios = false; // when native && !ios → Android path; when native && ios → iOS vault path
vi.mock('@/lib/platform', () => ({
  isNativeApp: () => native,
  isAndroid: () => native && !ios,
  isIOS: () => native && ios,
}));

const auth = { checkBiometry: vi.fn(), authenticate: vi.fn() };
const storage = { set: vi.fn(), get: vi.fn(), remove: vi.fn() };
const KeychainAccess = { whenPasscodeSetThisDeviceOnly: 4 };
// vi.mock factories are hoisted above const declarations — define the vault
// mock with vi.hoisted so it exists when the factory runs.
const vault = vi.hoisted(() => ({ isAvailable: vi.fn(), set: vi.fn(), get: vi.fn(), remove: vi.fn() }));
vi.mock('@aparajita/capacitor-biometric-auth', () => ({ BiometricAuth: auth }));
vi.mock('@aparajita/capacitor-secure-storage', () => ({ SecureStorage: storage, KeychainAccess }));
vi.mock('@/lib/biometricVault', () => ({ BiometricVault: vault }));

import { biometric, getDeviceId } from '../biometric';

beforeEach(() => {
  native = true;
  ios = false;
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

  describe('Android (secure-storage) path', () => {
    it('enroll stores the secret device-only', async () => {
      storage.set.mockResolvedValue(undefined);
      await biometric.enroll('child:1', 'Maya', 'secret-xyz');
      // (key, data, convertDate=false, sync=false, access=whenPasscodeSetThisDeviceOnly)
      expect(storage.set).toHaveBeenCalledWith('bio_child_1', 'secret-xyz', false, false, 4);
      expect(vault.set).not.toHaveBeenCalled();
    });

    it('unlockRead verifies then reads → ok', async () => {
      auth.authenticate.mockResolvedValue(undefined);
      storage.get.mockResolvedValue('secret-xyz');
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'ok', secret: 'secret-xyz' });
    });

    it('unlockRead → cancelled when verify fails', async () => {
      auth.authenticate.mockRejectedValue(new Error('cancelled'));
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'cancelled' });
      expect(storage.get).not.toHaveBeenCalled();
    });

    it('unlockRead → gone when the secret is absent', async () => {
      auth.authenticate.mockResolvedValue(undefined);
      storage.get.mockResolvedValue(null);
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'gone' });
    });

    it('clear removes the key and swallows missing-key errors', async () => {
      storage.remove.mockRejectedValue(new Error('not found'));
      await expect(biometric.clear('child:1')).resolves.toBeUndefined();
      expect(storage.remove).toHaveBeenCalledWith('bio_child_1');
    });
  });

  describe('iOS (biometric-bound vault) path', () => {
    beforeEach(() => { ios = true; });

    it('enroll writes to the vault, not secure-storage', async () => {
      vault.set.mockResolvedValue(undefined);
      await biometric.enroll('child:1', 'Maya', 'secret-xyz');
      expect(vault.set).toHaveBeenCalledWith({ key: 'bio_child_1', value: 'secret-xyz' });
      expect(storage.set).not.toHaveBeenCalled();
    });

    it('unlockRead → ok when the vault releases the secret', async () => {
      vault.get.mockResolvedValue({ value: 'secret-xyz' });
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'ok', secret: 'secret-xyz' });
      expect(vault.get).toHaveBeenCalledWith({ key: 'bio_child_1', reason: 'Unlock' });
      expect(auth.authenticate).not.toHaveBeenCalled(); // no separate prompt — the vault read IS the prompt
    });

    it('unlockRead → gone when the item was invalidated (re-enrolled biometrics)', async () => {
      vault.get.mockResolvedValue({});
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'gone' });
    });

    it('unlockRead → cancelled when the vault read rejects (cancel/auth-fail)', async () => {
      vault.get.mockRejectedValue(new Error('AUTH_FAILED'));
      expect(await biometric.unlockRead('child:1', 'Unlock')).toEqual({ status: 'cancelled' });
    });

    it('clear removes from the vault', async () => {
      vault.remove.mockResolvedValue(undefined);
      await biometric.clear('child:1');
      expect(vault.remove).toHaveBeenCalledWith({ key: 'bio_child_1' });
    });
  });
});
