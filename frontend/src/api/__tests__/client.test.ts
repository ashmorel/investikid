import { describe, it, expect, vi, afterEach } from 'vitest';

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
