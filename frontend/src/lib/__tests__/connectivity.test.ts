import { vi, describe, it, expect, beforeEach } from 'vitest';
import { onlineManager } from '@tanstack/react-query';

const listeners: Array<(s: { connected: boolean }) => void> = [];
vi.mock('@capacitor/network', () => ({
  Network: {
    getStatus: vi.fn(async () => ({ connected: false })),
    addListener: vi.fn((_e: string, cb: (s: { connected: boolean }) => void) => {
      listeners.push(cb);
      return Promise.resolve({ remove: vi.fn() });
    }),
  },
}));

import { initConnectivity } from '../connectivity';

describe('initConnectivity', () => {
  beforeEach(() => { listeners.length = 0; onlineManager.setOnline(true); });

  it('seeds onlineManager from Network.getStatus and updates on change', async () => {
    await initConnectivity();
    expect(onlineManager.isOnline()).toBe(false);   // seeded from getStatus
    listeners[0]({ connected: true });               // simulate reconnect
    expect(onlineManager.isOnline()).toBe(true);
  });

  it('swallows a plugin error and leaves onlineManager usable', async () => {
    const { Network } = await import('@capacitor/network');
    (Network.getStatus as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('no plugin'));
    await expect(initConnectivity()).resolves.toBeUndefined();
  });
});
