import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const apiFetch = vi.fn();
vi.mock('@/api/client', () => ({ apiFetch: (...a: unknown[]) => apiFetch(...a) }));

let native = true;
vi.mock('@/lib/platform', () => ({
  isNativeApp: () => native,
  isAndroid: () => false,
}));

const plugin = {
  checkPermissions: vi.fn(),
  requestPermissions: vi.fn(),
  addListener: vi.fn(),
  register: vi.fn(),
};
vi.mock('@capacitor/push-notifications', () => ({ PushNotifications: plugin }));

import { disablePush, enablePush, isPushRegistered } from '../push';

beforeEach(() => {
  native = true;
  localStorage.clear();
  vi.clearAllMocks();
  apiFetch.mockResolvedValue({ status: 'ok' });
  plugin.checkPermissions.mockResolvedValue({ receive: 'granted' });
  plugin.register.mockResolvedValue(undefined);
  plugin.addListener.mockImplementation((event: string, cb: (arg: { value: string }) => void) => {
    if (event === 'registration') setTimeout(() => cb({ value: 'tok-123' }), 0);
    return Promise.resolve({ remove: vi.fn() });
  });
});
afterEach(() => localStorage.clear());

describe('push consent gating (m7)', () => {
  it('no-ops on web', async () => {
    native = false;
    expect(await enablePush(true)).toBe('unavailable');
    expect(plugin.register).not.toHaveBeenCalled();
  });

  it('no-ops when the parent switch is off, even on native', async () => {
    expect(await enablePush(false)).toBe('unavailable');
    expect(plugin.register).not.toHaveBeenCalled();
  });

  it('registers the token with the backend when both gates pass', async () => {
    const result = await enablePush(true);
    expect(result).toBe('registered');
    expect(apiFetch).toHaveBeenCalledWith('/users/me/push-devices', expect.objectContaining({ method: 'POST' }));
    expect(isPushRegistered()).toBe(true);
  });

  it('reports permission denial without registering', async () => {
    plugin.checkPermissions.mockResolvedValue({ receive: 'prompt' });
    plugin.requestPermissions.mockResolvedValue({ receive: 'denied' });
    expect(await enablePush(true)).toBe('permission-denied');
    expect(plugin.register).not.toHaveBeenCalled();
  });

  it('disablePush unregisters the stored token', async () => {
    await enablePush(true);
    await disablePush();
    expect(apiFetch).toHaveBeenCalledWith('/users/me/push-devices/tok-123', expect.objectContaining({ method: 'DELETE' }));
    expect(isPushRegistered()).toBe(false);
  });
});
