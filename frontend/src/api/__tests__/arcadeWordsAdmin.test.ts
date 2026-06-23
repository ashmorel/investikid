import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { listArcadeWords, approveArcadeWord } from '../arcadeWordsAdmin';

describe('arcadeWordsAdmin api', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('GETs arcade words with status query param', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue([] as never);
    await listArcadeWords('pending');
    expect(spy).toHaveBeenCalledWith(`/admin/arcade-words?status=${encodeURIComponent('pending')}`);
  });

  it('GETs arcade words with custom status', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue([] as never);
    await listArcadeWords('approved');
    expect(spy).toHaveBeenCalledWith(`/admin/arcade-words?status=${encodeURIComponent('approved')}`);
  });

  it('POSTs approve with word id', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(null as never);
    await approveArcadeWord('abc-123');
    expect(spy).toHaveBeenCalledWith(
      '/admin/arcade-words/abc-123/approve',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('POSTs approve with edits', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(null as never);
    await approveArcadeWord('abc-123', { word: 'BUDGET', definition: 'A plan for money' });
    expect(spy).toHaveBeenCalledWith(
      '/admin/arcade-words/abc-123/approve',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ word: 'BUDGET', definition: 'A plan for money' }),
      }),
    );
  });
});
