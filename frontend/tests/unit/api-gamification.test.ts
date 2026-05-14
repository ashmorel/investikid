import { describe, it, expect, vi, beforeEach } from 'vitest';
import { gamificationApi } from '@/api/gamification';

beforeEach(() => vi.restoreAllMocks());

describe('gamificationApi', () => {
  it('getAllBadges calls GET /badges', async () => {
    const body = [{ id: '1', name: 'First Step', description: 'd', icon_url: '/x.svg', condition_type: 'lesson_count', condition_value: 1, earned_at: null }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const result = await gamificationApi.getAllBadges();
    expect(result).toEqual(body);
    expect(fetch).toHaveBeenCalledWith('/badges', expect.objectContaining({ method: 'GET' }));
  });

  it('getEarnedBadges calls GET /users/me/badges', async () => {
    const body = [{ id: '1', name: 'First Step', description: 'd', icon_url: '/x.svg', earned_at: '2026-01-01T00:00:00Z' }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const result = await gamificationApi.getEarnedBadges();
    expect(result).toEqual(body);
    expect(fetch).toHaveBeenCalledWith('/users/me/badges', expect.objectContaining({ method: 'GET' }));
  });

  it('getChallenges calls GET /challenges', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const result = await gamificationApi.getChallenges();
    expect(result).toEqual([]);
    expect(fetch).toHaveBeenCalledWith('/challenges', expect.objectContaining({ method: 'GET' }));
  });

  it('getLeaderboard calls GET /leaderboard', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const result = await gamificationApi.getLeaderboard();
    expect(result).toEqual([]);
    expect(fetch).toHaveBeenCalledWith('/leaderboard', expect.objectContaining({ method: 'GET' }));
  });
});
