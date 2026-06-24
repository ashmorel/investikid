import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { gamificationApi } from '../gamification';

describe('gamificationApi.getLeaderboard', () => {
  beforeEach(() => vi.restoreAllMocks());
  it('passes scope + metric as query params', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue([]);
    await gamificationApi.getLeaderboard('global', 'arcade');
    expect(spy).toHaveBeenCalledWith('/leaderboard?scope=global&metric=arcade');
  });
  it('reroll posts to /me/handle/reroll', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ handle: 'X' });
    await gamificationApi.rerollHandle();
    expect(spy).toHaveBeenCalledWith('/me/handle/reroll', { method: 'POST' });
  });
});
