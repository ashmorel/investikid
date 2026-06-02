import { describe, it, expect } from 'vitest';
import { pickTargetModule, pickTargetLevel, pickTargetLesson, buildHeroGreeting } from '@/lib/homeHero';
import type { ModuleOut, LevelOut, LessonSummary } from '@/api/content';

const mod = (id: string, order: number, locked = false): ModuleOut => ({
  id, topic: 'stocks', title: `M${id}`, country_codes: [], is_premium: false, order_index: order, icon: '📈', locked,
});

describe('pickTargetModule', () => {
  it('prefers continue_learning', () => {
    const r = pickTargetModule({ continue_learning: [{ module_id: 'c' }], something_new: [{ module_id: 'n' }] } as never, [mod('a', 0)]);
    expect(r).toEqual({ moduleId: 'c', mode: 'continue' });
  });
  it('falls back to something_new', () => {
    const r = pickTargetModule({ continue_learning: [], something_new: [{ module_id: 'n' }] } as never, [mod('a', 0)]);
    expect(r).toEqual({ moduleId: 'n', mode: 'start' });
  });
  it('falls back to first unlocked module by order', () => {
    const r = pickTargetModule({ continue_learning: [], something_new: [] } as never, [mod('b', 2), mod('a', 1), mod('locked', 0, true)]);
    expect(r).toEqual({ moduleId: 'a', mode: 'start' });
  });
  it('returns null when nothing available', () => {
    expect(pickTargetModule(null, [mod('x', 0, true)])).toBeNull();
  });
});

const lvl = (id: string, order: number, state: LevelOut['state'], done: number, total: number): LevelOut => ({
  id, module_id: 'm', title: id, order_index: order, is_premium: false, icon: '📊', state, locked_reason: null, passed: false, lessons_total: total, lessons_completed: done,
});

describe('pickTargetLevel', () => {
  it('returns first unlocked, not-complete level by order', () => {
    const r = pickTargetLevel([lvl('l2', 1, 'in_progress', 0, 3), lvl('l1', 0, 'completed', 3, 3)]);
    expect(r?.id).toBe('l2');
  });
  it('skips locked levels', () => {
    const r = pickTargetLevel([lvl('l1', 0, 'locked', 0, 3)]);
    expect(r).toBeNull();
  });
  it('returns null when all complete', () => {
    expect(pickTargetLevel([lvl('l1', 0, 'completed', 3, 3)])).toBeNull();
  });
});

const lsn = (id: string, order: number, completed: boolean): LessonSummary => ({
  id, type: 'quiz', title: `L${id}`, xp_reward: 10, order_index: order, completed,
});

describe('pickTargetLesson', () => {
  it('returns first incomplete lesson by order', () => {
    const r = pickTargetLesson([lsn('b', 1, false), lsn('a', 0, true)]);
    expect(r?.id).toBe('b');
  });
  it('returns null when all complete', () => {
    expect(pickTargetLesson([lsn('a', 0, true)])).toBeNull();
  });
});

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
