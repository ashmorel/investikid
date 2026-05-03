import { describe, it, expect } from 'vitest';
import { isStreakActive } from '@/lib/streak';

describe('isStreakActive', () => {
  const today = new Date('2026-05-02T12:00:00Z');

  it('null last_activity_date → not active', () => {
    expect(isStreakActive(null, today)).toBe(false);
  });
  it('last activity today → active', () => {
    expect(isStreakActive('2026-05-02', today)).toBe(true);
  });
  it('last activity yesterday → active (still in grace window)', () => {
    expect(isStreakActive('2026-05-01', today)).toBe(true);
  });
  it('last activity 2 days ago → not active', () => {
    expect(isStreakActive('2026-04-30', today)).toBe(false);
  });
});
