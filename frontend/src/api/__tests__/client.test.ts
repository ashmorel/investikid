import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { apiFetch, ApiError } from '@/api/client';

function jsonRes(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: String(status),
    json: async () => body,
  } as Response;
}

describe('apiFetch refresh-on-401', () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    document.cookie = '';
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('refreshes then retries once on 401, returning the retried body', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonRes(401, { detail: 'expired' }))   // original
      .mockResolvedValueOnce(jsonRes(200, { ok: true }))            // /auth/refresh
      .mockResolvedValueOnce(jsonRes(200, { data: 42 }));           // retry
    const out = await apiFetch<{ data: number }>('/users/me');
    expect(out).toEqual({ data: 42 });
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls.filter((u) => u.endsWith('/auth/refresh'))).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('shares ONE refresh across concurrent 401s (single-flight)', async () => {
    let firstA = true, firstB = true;
    fetchMock.mockImplementation(async (url: string) => {
      const u = String(url);
      if (u.endsWith('/auth/refresh')) return jsonRes(200, { ok: true });
      if (u.endsWith('/a')) { if (firstA) { firstA = false; return jsonRes(401, { detail: 'x' }); } return jsonRes(200, { p: 'a' }); }
      if (firstB) { firstB = false; return jsonRes(401, { detail: 'x' }); } return jsonRes(200, { p: 'b' });
    });
    const [a, b] = await Promise.all([apiFetch('/a'), apiFetch('/b')]);
    expect(a).toEqual({ p: 'a' });
    expect(b).toEqual({ p: 'b' });
    const refreshes = fetchMock.mock.calls.filter((c) => String(c[0]).endsWith('/auth/refresh'));
    expect(refreshes).toHaveLength(1);
  });

  it('throws the original 401 when refresh fails (no loop)', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonRes(401, { detail: 'expired' }))  // original
      .mockResolvedValueOnce(jsonRes(401, { detail: 'no rt' }));   // /auth/refresh fails
    await expect(apiFetch('/users/me')).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(2); // no retry
  });

  it('does not refresh for auth endpoints themselves', async () => {
    fetchMock.mockResolvedValueOnce(jsonRes(401, { detail: 'bad creds' }));
    await expect(apiFetch('/auth/login', { method: 'POST', body: '{}' })).rejects.toBeInstanceOf(ApiError);
    expect(fetchMock).toHaveBeenCalledTimes(1); // no /auth/refresh
  });
});

describe('apiFetch base URL', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uses relative path when VITE_API_BASE_URL is empty', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
    );
    const { apiFetch } = await import('@/api/client');
    await apiFetch('/health');
    expect(fetchSpy.mock.calls[0][0]).toBe('/health');
  });

  it('prepends base URL when VITE_API_BASE_URL is set', async () => {
    // Save original and override
    const original = import.meta.env.VITE_API_BASE_URL;
    import.meta.env.VITE_API_BASE_URL = 'https://api.example.com';
    vi.resetModules();
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
    );
    const { apiFetch } = await import('@/api/client');
    await apiFetch('/health');
    expect(fetchSpy.mock.calls[0][0]).toBe('https://api.example.com/health');
    // Restore
    import.meta.env.VITE_API_BASE_URL = original;
  });
});
