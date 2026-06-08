import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, ApiError } from '@/api/client';

describe('apiFetch premium error', () => {
  beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('exposes code + context from a structured detail', async () => {
    (globalThis.fetch as any).mockResolvedValue(new Response(JSON.stringify({
      detail: { message: 'Premium required', code: 'premium_required',
                context: { kind: 'level', label: 'Investing Basics' } },
    }), { status: 403 }));
    try {
      await apiFetch('/levels/x/lessons');
      throw new Error('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(403);
      expect(err.code).toBe('premium_required');
      expect((err.context as any).kind).toBe('level');
      expect(err.detail).toBe('Premium required');
    }
  });

  it('still works with a plain string detail', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Nope' }), { status: 400 }));
    await expect(apiFetch('/x')).rejects.toMatchObject({ status: 400, detail: 'Nope' });
  });
});
