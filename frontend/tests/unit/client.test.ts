import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { apiFetch } from '@/api/client';

describe('apiFetch', () => {
  beforeEach(() => {
    document.cookie = 'csrf_token=test-csrf';
    vi.spyOn(globalThis, 'fetch');
  });
  afterEach(() => {
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    vi.restoreAllMocks();
  });

  it('attaches X-CSRF-Token header on POST', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await apiFetch('/parent/children/x/freeze', { method: 'POST', body: '{}' });
    const call = (globalThis.fetch as any).mock.calls[0];
    const init = call[1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers['X-CSRF-Token']).toBe('test-csrf');
    expect(init.credentials).toBe('include');
  });

  it('does NOT attach X-CSRF-Token on GET', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    await apiFetch('/parent/children');
    const call = (globalThis.fetch as any).mock.calls[0];
    const init = call[1] as RequestInit;
    const headers = (init.headers as Record<string, string>) ?? {};
    expect(headers['X-CSRF-Token']).toBeUndefined();
  });

  it('throws ApiError on non-OK with detail', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Link expired' }), { status: 410 }),
    );
    await expect(apiFetch('/consent/verify?token=x')).rejects.toMatchObject({
      status: 410, detail: 'Link expired',
    });
  });

  it('returns parsed JSON on 200', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    await expect(apiFetch('/x')).resolves.toEqual({ ok: true });
  });

  it('returns null on 204', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(null, { status: 204 }));
    await expect(apiFetch('/x')).resolves.toBeNull();
  });
});
