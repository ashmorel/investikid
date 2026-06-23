import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { getMoneyWordToday, submitMoneyWordGuess } from '../moneyword';

describe('moneyword api', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('GETs the today puzzle', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(null as never);
    await getMoneyWordToday();
    expect(spy).toHaveBeenCalledWith('/arcade/moneyword/today');
  });

  it('POSTs a guess with body', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(null as never);
    await submitMoneyWordGuess('MONEY');
    expect(spy).toHaveBeenCalledWith(
      '/arcade/moneyword/guess',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ guess: 'MONEY' }) }),
    );
  });
});
