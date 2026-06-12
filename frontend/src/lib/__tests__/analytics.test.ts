import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({ apiFetch: vi.fn() }));

import { apiFetch } from '@/api/client';
import { resetForTests, track, trackOncePerSession } from '../analytics';

const mockedFetch = vi.mocked(apiFetch);

describe('analytics track()', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedFetch.mockResolvedValue({ accepted: 1, dropped: 0 });
    resetForTests();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('batches queued events into one debounced POST', async () => {
    track('home_view');
    track('home_cta_tap', { surface: 'hero' });
    expect(mockedFetch).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(5_000);
    expect(mockedFetch).toHaveBeenCalledTimes(1);
    const [path, init] = mockedFetch.mock.calls[0];
    expect(path).toBe('/analytics/events');
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.events).toEqual([
      { event_name: 'home_view' },
      { event_name: 'home_cta_tap', props: { surface: 'hero' } },
    ]);
    expect((init as RequestInit & { keepalive?: boolean }).keepalive).toBe(true);
  });

  it('caps a flush at 20 events and sends the rest next flush', async () => {
    for (let i = 0; i < 25; i++) track('home_view');
    await vi.advanceTimersByTimeAsync(5_000);
    expect(mockedFetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse((mockedFetch.mock.calls[0][1] as RequestInit).body as string);
    expect(body.events).toHaveLength(20);
    await vi.advanceTimersByTimeAsync(5_000);
    expect(mockedFetch).toHaveBeenCalledTimes(2);
  });

  it('swallows network failures silently', async () => {
    mockedFetch.mockRejectedValueOnce(new Error('boom'));
    track('home_view');
    await expect(vi.advanceTimersByTimeAsync(5_000)).resolves.not.toThrow();
  });

  it('drops events while offline', async () => {
    const spy = vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false);
    track('home_view');
    await vi.advanceTimersByTimeAsync(5_000);
    expect(mockedFetch).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it('trackOncePerSession only fires once until reset', async () => {
    trackOncePerSession('home_view');
    trackOncePerSession('home_view');
    await vi.advanceTimersByTimeAsync(5_000);
    expect(mockedFetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse((mockedFetch.mock.calls[0][1] as RequestInit).body as string);
    expect(body.events).toHaveLength(1);
  });
});
