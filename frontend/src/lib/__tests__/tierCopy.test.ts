import { describe, it, expect } from 'vitest';
import { buildHeroGreeting } from '../homeHero';
import { ENCOURAGEMENT } from '../tierCopy';

const base = { name: 'Sam', mode: 'start' as const, lessonLabel: 'Stocks 101', streakCount: 0, dueCount: 0 };

describe('tier-aware hero greeting', () => {
  const variants = [
    { label: 'start', extra: { mode: 'start' as const, dueCount: 0 } },
    { label: 'continue', extra: { mode: 'continue' as const, dueCount: 0, streakCount: 3 } },
    { label: 'caught_up', extra: { mode: 'caught_up' as const, dueCount: 0 } },
    { label: 'due', extra: { mode: 'start' as const, dueCount: 2 } },
  ];

  it('explorer copy is warm and uses an emoji', () => {
    const g = buildHeroGreeting({ ...base, tier: 'explorer' });
    expect(g).toContain('Sam');
    expect(/\p{Extended_Pictographic}/u.test(g)).toBe(true);
  });

  it.each(variants)('investor copy is emoji-free ($label)', ({ extra }) => {
    const g = buildHeroGreeting({ ...base, ...extra, tier: 'investor' });
    expect(g).toContain('Sam');
    expect(/\p{Extended_Pictographic}/u.test(g)).toBe(false);
  });
});

describe('tier encouragement lines', () => {
  it('provides a non-empty set for each tier', () => {
    expect(ENCOURAGEMENT.explorer.length).toBeGreaterThan(0);
    expect(ENCOURAGEMENT.investor.length).toBeGreaterThan(0);
  });
});
