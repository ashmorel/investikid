import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { premiumApi } from '@/api/premium';
import { PREMIUM_BENEFITS } from '@/lib/premiumConfig';

describe('premiumApi', () => {
  beforeEach(() => { document.cookie = 'csrf_token=t'; vi.spyOn(globalThis, 'fetch'); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('requestUnlock POSTs kind+label', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({ status: 'sent' }), { status: 200 }));
    const res = await premiumApi.requestUnlock({ kind: 'level', label: 'Investing Basics' });
    expect(res?.status).toBe('sent');
    const [path, init] = (globalThis.fetch as any).mock.calls[0];
    expect(path).toContain('/premium/request');
    expect(JSON.parse(init.body)).toEqual({ kind: 'level', label: 'Investing Basics' });
  });

  it('benefits are non-empty', () => { expect(PREMIUM_BENEFITS.length).toBeGreaterThan(0); });
});
