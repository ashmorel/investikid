import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { getQuizRushSession, submitQuizRushScore } from '../arcade';

describe('arcade api', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('GETs a quiz-rush session', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ items: [] } as never);
    await getQuizRushSession();
    expect(spy).toHaveBeenCalledWith('/arcade/quiz-rush/session');
  });

  it('POSTs a score submission', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(
      { points: 0, coins_awarded: 0, personal_best: 0, leaderboard_rank: null } as never,
    );
    await submitQuizRushScore({ session_items: [], answers: [] });
    expect(spy).toHaveBeenCalledWith('/arcade/quiz-rush/score', expect.objectContaining({ method: 'POST' }));
  });
});
