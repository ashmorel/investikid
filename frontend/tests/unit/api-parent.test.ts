import { describe, it, expect, vi, beforeEach } from 'vitest';
import { parentApi } from '@/api/parent';

beforeEach(() => {
  document.cookie = 'csrf_token=ct';
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
  );
});

describe('parentApi', () => {
  it('listChildren is a GET', async () => {
    await parentApi.listChildren();
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe('/parent/children');
    expect(call[1].method).toBe('GET');
  });

  it('freezeChild posts JSON body and CSRF header', async () => {
    await parentApi.freezeChild('uid-1', true);
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe('/parent/children/uid-1/freeze');
    expect(call[1].method).toBe('POST');
    expect((call[1].headers as any)['X-CSRF-Token']).toBe('ct');
    expect(JSON.parse(call[1].body)).toEqual({ frozen: true });
  });

  it('eraseChild posts with CSRF header', async () => {
    await parentApi.eraseChild('uid-2');
    const call = (globalThis.fetch as any).mock.calls[0];
    expect(call[0]).toBe('/parent/children/uid-2/erasure');
    expect((call[1].headers as any)['X-CSRF-Token']).toBe('ct');
  });
});
