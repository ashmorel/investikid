import { describe, it, expect, beforeEach, vi } from 'vitest';
import { isNudgeDismissed, dismissNudge, DISMISS_DAYS } from '@/lib/premiumNudge';

beforeEach(() => localStorage.clear());

describe('premiumNudge', () => {
  it('not dismissed by default', () => {
    expect(isNudgeDismissed('home-upsell')).toBe(false);
  });
  it('dismiss persists and reads back dismissed', () => {
    dismissNudge('home-upsell');
    expect(isNudgeDismissed('home-upsell')).toBe(true);
  });
  it(`re-appears after ${DISMISS_DAYS} days`, () => {
    dismissNudge('k');
    const future = Date.now() + (DISMISS_DAYS + 1) * 24 * 60 * 60 * 1000;
    vi.spyOn(Date, 'now').mockReturnValue(future);
    expect(isNudgeDismissed('k')).toBe(false);
    vi.restoreAllMocks();
  });
  it('treats unavailable localStorage as not-dismissed', () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('nope'); });
    expect(isNudgeDismissed('k')).toBe(false);
    spy.mockRestore();
  });
});
