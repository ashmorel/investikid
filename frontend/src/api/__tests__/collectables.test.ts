import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { getCollectables } from '../collectables';

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
}));

describe('getCollectables', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('calls GET /collectables', async () => {
    const payload = { active: [], owned: [] };
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(payload as never);
    await getCollectables();
    expect(spy).toHaveBeenCalledWith('/collectables');
  });

  it('returns active drops and owned collectables', async () => {
    const payload = {
      active: [
        {
          slug: 'streak-legend',
          name: 'Streak Legend',
          emoji: '🔥',
          type: 'accessory',
          rarity: 'legendary',
          ends_at: '2026-07-01T00:00:00Z',
          goal: { type: 'streak_days', threshold: 7, current: 3 },
          earned: false,
        },
      ],
      owned: [],
    };
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(payload as never);
    const result = await getCollectables();
    expect(spy).toHaveBeenCalledWith('/collectables');
    expect(result).toEqual(payload);
  });
});
