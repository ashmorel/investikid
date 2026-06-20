import { describe, it, expect } from 'vitest';
import { makeChallenge, checkAnswer } from '../parentalGate';

describe('parentalGate logic', () => {
  it('produces a multiplication challenge with a numeric answer', () => {
    const c = makeChallenge(() => 0.5); // deterministic rng
    expect(c.prompt).toMatch(/\d+\s*×\s*\d+/);
    expect(typeof c.answer).toBe('number');
    expect(c.answer).toBe(c.a * c.b);
  });
  it('accepts the exact answer and rejects others', () => {
    const c = makeChallenge(() => 0.5);
    expect(checkAnswer(c, String(c.answer))).toBe(true);
    expect(checkAnswer(c, String(c.answer + 1))).toBe(false);
    expect(checkAnswer(c, '')).toBe(false);
    expect(checkAnswer(c, 'abc')).toBe(false);
  });
});
