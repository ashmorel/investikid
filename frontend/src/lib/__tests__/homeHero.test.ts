import { describe, it, expect } from 'vitest';
import { buildHeroGreeting } from '@/lib/homeHero';

describe('buildHeroGreeting', () => {
  it('start mode names the lesson', () => {
    expect(buildHeroGreeting({ name: 'Sam', mode: 'start', lessonLabel: 'What is a Stock?', streakCount: 0, dueCount: 0 })).toContain('What is a Stock?');
  });
  it('continue mode welcomes back', () => {
    expect(buildHeroGreeting({ name: 'Sam', mode: 'continue', lessonLabel: 'Compound Interest', streakCount: 3, dueCount: 0 })).toMatch(/Welcome back, Sam/);
  });
  it('reviews due takes priority', () => {
    expect(buildHeroGreeting({ name: 'Sam', mode: 'start', lessonLabel: 'X', streakCount: 0, dueCount: 2 })).toContain('2 concepts');
  });
  it('caught_up celebrates', () => {
    expect(buildHeroGreeting({ name: 'Sam', mode: 'caught_up', lessonLabel: null, streakCount: 0, dueCount: 0 })).toMatch(/finished everything/);
  });
});
