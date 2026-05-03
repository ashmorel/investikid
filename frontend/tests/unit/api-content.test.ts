import { describe, it, expect, vi, beforeEach } from 'vitest';
import { contentApi } from '@/api/content';

beforeEach(() => vi.restoreAllMocks());

describe('contentApi', () => {
  it('listModules calls GET /modules', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    await contentApi.listModules();
    expect(fetchSpy).toHaveBeenCalledWith('/modules', expect.objectContaining({ method: 'GET' }));
  });

  it('listLessons calls GET /modules/:id/lessons', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    await contentApi.listLessons('mod-1');
    expect(fetchSpy).toHaveBeenCalledWith('/modules/mod-1/lessons', expect.objectContaining({ method: 'GET' }));
  });

  it('getLesson calls GET /lessons/:id', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 }),
    );
    await contentApi.getLesson('les-1');
    expect(fetchSpy).toHaveBeenCalledWith('/lessons/les-1', expect.objectContaining({ method: 'GET' }));
  });

  it('completeLesson POSTs with score', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ xp_awarded: 10, already_completed: false, total_xp: 10, level: 1, streak_count: 1 }),
        { status: 200 }),
    );
    await contentApi.completeLesson('les-1', 0.5);
    expect(fetchSpy).toHaveBeenCalledWith(
      '/lessons/les-1/complete',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ score: 0.5 }),
      }),
    );
  });

  it('getProgress calls GET /users/me/progress', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ xp: 0, level: 1, streak_count: 0, last_activity_date: null }),
        { status: 200 }),
    );
    await contentApi.getProgress();
    expect(fetchSpy).toHaveBeenCalledWith('/users/me/progress', expect.objectContaining({ method: 'GET' }));
  });
});
