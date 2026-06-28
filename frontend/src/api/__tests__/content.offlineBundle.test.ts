import { describe, it, expect, vi, beforeEach } from 'vitest';

const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }));
vi.mock('@/api/client', () => ({ apiFetch }));

import { getOfflineBundle } from '../content';

beforeEach(() => {
  apiFetch.mockReset();
  apiFetch.mockResolvedValue({});
});

describe('getOfflineBundle URL', () => {
  it('hits the root-mounted /offline-bundle path (no /content prefix) when since is null', async () => {
    await getOfflineBundle(null);
    expect(apiFetch).toHaveBeenCalledWith('/offline-bundle');
  });

  it('URL-encodes the since cursor (a raw +00:00 offset must not reach the query string)', async () => {
    await getOfflineBundle('2026-06-28T12:00:00+00:00');
    expect(apiFetch).toHaveBeenCalledWith(
      '/offline-bundle?since=2026-06-28T12%3A00%3A00%2B00%3A00',
    );
  });
});
