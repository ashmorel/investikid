import { describe, it, expect, vi, beforeEach } from 'vitest';
import { consentApi } from '@/api/consent';

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ username: 'kid', age: 11, country_code: 'GB' }), { status: 200 }),
  );
});

describe('consentApi', () => {
  it('verify hits the right URL with encoded token', async () => {
    await consentApi.verify('a/b=c');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/consent/verify?token=a%2Fb%3Dc',
      expect.any(Object),
    );
  });

  it('decide POSTs body', async () => {
    await consentApi.decide('tok', 'approve');
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe('/consent/decide?token=tok');
    expect(call[1].method).toBe('POST');
    expect(JSON.parse(call[1].body)).toEqual({ decision: 'approve', attest_guardian: false });
  });
});
