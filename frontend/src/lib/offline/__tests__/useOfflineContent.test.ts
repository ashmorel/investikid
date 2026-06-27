import { describe, it, expect, vi, beforeEach } from 'vitest';
vi.mock('../sqlite', () => ({ isOfflineDbAvailable: vi.fn(() => true) }));
import { isOfflineDbAvailable } from '../sqlite';
import type { CacheScope } from '../scope';
import { cacheFirst } from '../useOfflineContent';

const scope: CacheScope = { childId: 'C1', market: 'GB' };
beforeEach(() => vi.clearAllMocks());

describe('cacheFirst', () => {
  it('online: fetches, writes through, returns data', async () => {
    const write = vi.fn(async () => {});
    const read = vi.fn(async () => null);
    const fn = cacheFirst({ scope, fetch: async () => ({ id: 'L1' }), read, write });
    expect(await fn()).toEqual({ id: 'L1' });
    expect(write).toHaveBeenCalledWith(scope, { id: 'L1' });
    expect(read).not.toHaveBeenCalled();
  });

  it('offline: fetch fails, returns cached read', async () => {
    const fn = cacheFirst({ scope, fetch: async () => { throw new Error('net'); }, read: async () => ({ id: 'cached' }), write: async () => {} });
    expect(await fn()).toEqual({ id: 'cached' });
  });

  it('offline + no cache: rethrows the original error', async () => {
    const err = new Error('net');
    const fn = cacheFirst({ scope, fetch: async () => { throw err; }, read: async () => null, write: async () => {} });
    await expect(fn()).rejects.toBe(err);
  });

  it('unavailable / null scope: passes through fetch, no read/write', async () => {
    vi.mocked(isOfflineDbAvailable).mockReturnValue(false);
    const write = vi.fn(async () => {});
    const fn = cacheFirst({ scope: null, fetch: async () => ({ id: 'L1' }), read: async () => null, write });
    expect(await fn()).toEqual({ id: 'L1' });
    expect(write).not.toHaveBeenCalled();
  });
});
