import { describe, it, expect, vi, beforeEach } from 'vitest';
import { missionsApi } from '@/api/missions';

beforeEach(() => vi.restoreAllMocks());

function mockFetch(body: unknown, status = 200) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  );
}

describe('missionsApi', () => {
  it('getActive calls GET /missions/active', async () => {
    const spy = mockFetch([
      { id: 'm1', lesson_id: 'l1', mission_type: 'first_buy', title: 'Buy one', prompt: 'Try it', params_json: {} },
    ]);
    const res = await missionsApi.getActive();
    expect(spy).toHaveBeenCalledWith('/missions/active', expect.objectContaining({ method: 'GET' }));
    expect(res?.[0].mission_type).toBe('first_buy');
  });
});
