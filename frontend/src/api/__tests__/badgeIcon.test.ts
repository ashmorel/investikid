import { describe, it, expect } from 'vitest';
import { badgeIcon } from '@/api/admin';

describe('badgeIcon', () => {
  it('uses a stored emoji', () => {
    expect(badgeIcon({ icon_url: '🔥', condition_type: 'streak_days' })).toBe('🔥');
  });

  it('falls back to a condition icon when icon_url is a dead /badges path', () => {
    expect(badgeIcon({ icon_url: '/badges/first-step.svg', condition_type: 'lesson_count' })).toBe('📚');
    expect(badgeIcon({ icon_url: '/badges/streak.svg', condition_type: 'streak_days' })).toBe('🔥');
    expect(badgeIcon({ icon_url: '/badges/trade.svg', condition_type: 'trade_count' })).toBe('📈');
    expect(badgeIcon({ icon_url: '/badges/xp.svg', condition_type: 'total_xp' })).toBe('⭐');
  });

  it('falls back for an http url and for an empty value', () => {
    expect(badgeIcon({ icon_url: 'https://x/y.png', condition_type: 'lesson_count' })).toBe('📚');
    expect(badgeIcon({ icon_url: '', condition_type: 'lesson_count' })).toBe('📚');
  });

  it('uses a generic medal for an unknown condition with no emoji', () => {
    expect(badgeIcon({ icon_url: '/badges/x.svg', condition_type: 'mystery' })).toBe('🏅');
  });
});
